"""Shared helpers for the Story 30.3 doc generators (spec-pyforge-doctor
CAP-84): ``scripts/docs_pixi_tasks.py``, ``docs_station_cli.py``,
``docs_detectors.py``, ``docs_skills_catalog.py``, ``docs_environments.py``,
and the two that followed them, ``docs_github_workflows.py`` (Story 59.1)
and ``docs_station_verify.py`` (Story 60.2).

Not itself a pixi task or a detector -- no ``DETECTOR`` marker, no
``_check.py`` suffix, so ``scripts/detectors.py``'s ``discover()`` never
scans it (mirrors ``docs_map_render.py``'s own plain-mutator status). The
pieces genuinely shared across all of them: the ``derived_at``/
``tree`` stamp (herald ``facts.yaml``'s shape, ported from
``scripts/deck_facts.py``'s own ``head_info``), a minimal frontmatter
reader, and the write+stamp+``--check`` plumbing every generator's
``main()`` drives identically.

Determinism: ``tree`` is the HEAD sha and ``derived_at`` is the HEAD commit
DATE -- never wall-clock generation time -- so re-running a generator on an
unchanged tree writes byte-identical output no matter when it is run.

The ``-dirty`` suffix is scoped to the page (doctor Story 60.2). A generator
stamps through :func:`stamped_render`, and ``tree`` reads ``<sha>-dirty``
only when what the page derives from is uncommitted: a path the page's
``docs/map.yaml`` row declares under ``sources:`` is modified or untracked,
or the rendered body is not the body HEAD holds for the page. Any other
modified file -- ``docs/map.yaml`` itself, which every write updates,
included -- leaves the stamp clean. Before that story the flag covered the
whole working tree, so every stamp written on a branch with any edit at all
read ``-dirty``, and a second write on a clean tree did too (the first had
just modified ``docs/map.yaml``).

Deliberately does not import ``pyforge.doctor``: these generators must run
correctly in whichever environment invokes their own pixi task, without
depending on Doctor's package being importable there (the ``--check`` side
of the contract lives IN Doctor, via ``cli_bridge.run_check_script``
running this generator as a subprocess -- see ``sources/docs_currency.py``,
Story 30.3's ``generated-page-stale`` check).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def configure_root_argument(parser: argparse.ArgumentParser) -> None:
    """Optional ``--root`` for Doctor's ``docs_currency`` check (Story 40.2).

    Default behaviour (no ``--root``) keeps every ``pixi run docs-*`` task
    judging the checkout the generator lives in."""
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository root to read and judge (default: the checkout this script lives in)",
    )


def resolve_root(args: argparse.Namespace) -> Path:
    if args.root is not None:
        return args.root.resolve()
    return REPO_ROOT


# A top-level, single-line `description:` value -- the one field a failed
# frontmatter parse most needs to recover (see parse_frontmatter's fallback).
_DESCRIPTION_LINE_RE = re.compile(r"^description:[ \t]*(.+)$", re.MULTILINE)


class _IndentedListDumper(yaml.Dumper):
    """Standard PyYAML idiom: force block-sequence items to be indented
    under their parent key (``  - path:``) rather than PyYAML's default
    "indentless" style (``- path:`` flush with the key). docs/map.yaml's
    own hand-authored convention is the indented style -- without this,
    ``update_map_stamp``'s ``yaml.safe_dump`` would reformat every one of
    the ~90 untouched page entries as a side effect of updating one page's
    stamp (found live 2026-09-24: this module is the file's first-ever
    programmatic writer)."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _declared_sources(root: Path, page_rel: str) -> list[str]:
    """The ``sources:`` the page's ``docs/map.yaml`` row declares, or ``[]`` when the map is missing or
    unreadable, carries no row for the page, or the row declares none."""
    map_yaml = root / "docs" / "map.yaml"
    if not map_yaml.is_file():
        return []
    try:
        data = yaml.safe_load(map_yaml.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return []
    pages = data.get("pages") if isinstance(data, dict) else None
    for page in pages if isinstance(pages, list) else []:
        if isinstance(page, dict) and page.get("path") == page_rel:
            sources = page.get("sources")
            if not isinstance(sources, list):
                return []
            return [
                source
                for source in sources
                if isinstance(source, str) and source.strip()
            ]
    return []


def _head_page_body(root: Path, page_rel: str) -> str | None:
    """The page's body as HEAD holds it, stamp header stripped; ``None`` when HEAD does not hold the page."""
    result = subprocess.run(
        ["git", "show", f"HEAD:docs/{page_rel}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return _strip_stamp_header(result.stdout)


def _is_dirty(root: Path, page_rel: str | None, body: str | None) -> bool:
    sources = _declared_sources(root, page_rel) if page_rel is not None else []
    if not sources:
        # No page, or a row that declares no sources: nothing narrower to read than the whole tree.
        return bool(git(root, "status", "--porcelain", "--untracked-files=no"))
    # An untracked file under a declared source is read by the generator too, so it counts.
    if git(root, "status", "--porcelain", "--untracked-files=all", "--", *sources):
        return True
    return (
        body is not None
        and page_rel is not None
        and _head_page_body(root, page_rel) != body
    )


def head_stamp(
    root: Path, page_rel: str | None = None, body: str | None = None
) -> dict[str, str]:
    """``{"derived_at": ..., "tree": ...}`` -- HEAD commit date (ISO-8601,
    ``%cI``) and HEAD sha, ``-dirty``-suffixed when what the page derives
    from is uncommitted. Both come from the commit, not the clock, so two
    runs against the same tree state produce the identical pair.

    ``page_rel`` (the ``docs/``-relative page) scopes the dirty flag to the
    ``sources:`` its ``docs/map.yaml`` row declares, and ``body`` (a fresh
    render with its stamp header stripped) adds the page itself, compared
    with the body HEAD holds -- the stamp lines are never compared, since a
    committed page can never carry its own commit's sha. Without
    ``page_rel``, or for a row that declares no sources, the flag covers
    every tracked file, as it did before Story 60.2."""
    return {
        "derived_at": git(root, "log", "-1", "--format=%cI"),
        "tree": git(root, "rev-parse", "HEAD")
        + ("-dirty" if _is_dirty(root, page_rel, body) else ""),
    }


# Stand-ins for the two stamp values while the body is rendered (see stamped_render).
_PENDING_STAMP = {"derived_at": "@@docs-gen:derived_at@@", "tree": "@@docs-gen:tree@@"}


def stamped_render(
    root: Path, page_rel: str, render: Callable[[dict[str, str]], str]
) -> tuple[dict[str, str], str]:
    """``(stamp, content)`` for one generated page: ``render(stamp)`` is the generator's own render, called
    ONCE, and ``stamp`` is :func:`head_stamp` scoped to this page and to the body that render produced.

    The stamp depends on the body (is it what HEAD holds?) and the content embeds the stamp, so the body is
    rendered first with stand-in stamp values, which are then replaced in the header. A render that embeds no
    stamp comes back unchanged."""
    pending = render(dict(_PENDING_STAMP))
    stamp = head_stamp(root, page_rel, _strip_stamp_header(pending))
    content = pending
    for key, placeholder in _PENDING_STAMP.items():
        content = content.replace(placeholder, stamp[key], 1)
    return stamp, content


def render_header(generator_rel: str, task: str, stamp: dict[str, str]) -> str:
    """The GENERATED banner every page opens with -- names the generator,
    the pixi task that reruns it, and the stamp (facts.yaml's shape)."""
    return (
        f"<!-- GENERATED by {generator_rel} -- do not hand-edit. Regenerate with:\n"
        f"         pixi run -e pyforge-guild {task}\n"
        f"     derived_at: {stamp['derived_at']}\n"
        f"     tree: {stamp['tree']} -->\n"
    )


def _description_fallback(block: str) -> dict:
    """When ``block`` fails to parse as YAML, recover just the single-line
    ``description:`` value via regex rather than silently losing it.

    A plain-scalar ``description:`` value containing a mid-value ``": "``
    (e.g. ``description: Measure before optimizing. Five-step workflow:
    Measure -> ...``) is invalid unquoted YAML -- it reads as the start of a
    nested mapping -- so the WHOLE frontmatter block fails to parse. Found
    live 2026-09-24: ``idea-refine``, ``performance-optimization``,
    ``security-and-hardening`` and ``spec-driven-development`` all render
    blank descriptions in the skills catalog this way, with no finding
    raised anywhere (a caller's ``name`` fallback to the skill directory
    name already covers that field; ``description`` has no such fallback).
    Narrow on purpose: recovers the one field every caller actually needs
    when the full parse fails, not a general line-by-line re-parse."""
    match = _DESCRIPTION_LINE_RE.search(block)
    return {"description": match.group(1).strip()} if match else {}


def parse_frontmatter(text: str) -> dict:
    """Minimal ``---``-fenced YAML frontmatter reader. A second small copy
    of ``pyforge.doctor.sources.docs_currency``'s own
    ``_parse_page_frontmatter``, deliberately not imported from there: these
    generators must not depend on ``pyforge.doctor`` being importable in
    whichever environment runs their own pixi task."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            block = "\n".join(lines[1:index])
            try:
                data = yaml.safe_load(block)
            except yaml.YAMLError:
                return _description_fallback(block)
            return data if isinstance(data, dict) else {}
    return {}


def _strip_stamp_header(text: str) -> str:
    """Drop the ``<!-- GENERATED ... -->`` stamp block :func:`render_header`
    produces from the START of ``text``, if present -- everything from the
    opening ``<!-- GENERATED`` line through the first line containing
    ``-->``, inclusive.

    Used only to compare two renders for a REAL content difference: the
    stamp's ``derived_at``/``tree`` legitimately changes on every commit
    (including one that touches nothing this page derives from), so
    comparing full text would flag every generated page stale on every
    unrelated commit. Never used when writing -- the written file always
    keeps its stamp."""
    lines = text.splitlines(keepends=True)
    if not lines or not lines[0].startswith("<!-- GENERATED"):
        return text
    for index, line in enumerate(lines):
        if "-->" in line:
            return "".join(lines[index + 1 :])
    return text


def update_map_stamp(root: Path, page_rel: str, stamp: dict[str, str]) -> None:
    """Write ``stamp`` into ``docs/map.yaml``'s entry for ``page_rel`` (the
    ``docs/``-relative path, e.g. ``how-to/pixi-tasks.md``).

    Silently a no-op when ``map.yaml`` is missing/invalid or carries no
    entry for this page -- the generator's own page write already
    succeeded by the time this runs; a missing or malformed registry row is
    ``docs-map-hygiene``'s/``docs-currency``'s territory to report, not
    this helper's to raise over."""
    map_yaml = root / "docs" / "map.yaml"
    if not map_yaml.is_file():
        return
    try:
        data = yaml.safe_load(map_yaml.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return
    if not isinstance(data, dict):
        return
    pages = data.get("pages")
    if not isinstance(pages, list):
        return
    changed = False
    for page in pages:
        if isinstance(page, dict) and page.get("path") == page_rel:
            if page.get("stamp") != stamp:
                page["stamp"] = stamp
                changed = True
            break
    if changed:
        map_yaml.write_text(
            yaml.dump(
                data,
                Dumper=_IndentedListDumper,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )


def write_generated_page(
    root: Path,
    page_rel: str,
    content: str,
    *,
    check: bool,
    stamp: dict[str, str] | None = None,
) -> int:
    """The write+``--check`` plumbing every generator's ``main()`` shares.

    ``check=True``: compare ``content`` (a fresh in-memory render) against
    the page currently on disk, WITH EACH SIDE'S STAMP HEADER STRIPPED
    first (:func:`_strip_stamp_header`) -- the stamp's own ``derived_at``/
    ``tree`` legitimately differs on every commit, including one that
    touches nothing this page derives from, so comparing it would flag
    every generated page stale on any unrelated commit. Print + return 0
    when the stripped bodies match, 1 when they differ (stale -- a source
    moved past the stamp, a hand edit, or the page was never generated).
    Never writes, never touches ``docs/map.yaml`` -- this is the mode
    ``docs-currency``'s generated-page-stale check invokes via
    ``cli_bridge.run_check_script``.

    ``check=False``: write ``content`` (creating parent directories as
    needed), advance ``docs/map.yaml``'s stamp for this page to ``stamp``
    (the SAME dict the caller already embedded into ``content`` via
    :func:`render_header` -- passed through rather than recomputed, so a
    write is exactly one extra git read, not three), print whether the
    page's bytes actually changed, and return 0 -- writing always succeeds
    once the render itself didn't raise. ``stamp=None`` skips the
    ``docs/map.yaml`` update entirely (a caller with no stamp to record).
    """
    page_path = root / "docs" / page_rel
    current = page_path.read_text(encoding="utf-8") if page_path.is_file() else None

    if check:
        if current is not None and _strip_stamp_header(current) == _strip_stamp_header(
            content
        ):
            print(f"[{page_rel}] current")
            return 0
        print(
            f"[{page_rel}] STALE -- regenerate with the matching guild-tasks pixi task",
            file=sys.stderr,
        )
        return 1

    page_path.parent.mkdir(parents=True, exist_ok=True)
    changed = current != content
    page_path.write_text(content, encoding="utf-8")
    if stamp is not None:
        update_map_stamp(root, page_rel, stamp)
    print(
        f"[{page_rel}] {'wrote' if changed else 'unchanged'} ({'changed' if changed else 'no content change'})"
    )
    return 0
