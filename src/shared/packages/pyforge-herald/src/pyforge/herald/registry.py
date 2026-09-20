"""A deck README's own § *Design project* section (Story 1.5, AD-8).

Every hand-seeded ``presentations/<slug>/README.md`` carries a human-readable
``## Design project (the bridge's far end)`` section naming the linked Claude
Design project -- this module is its sole owner: ``register`` appends the
section when a README has none yet, or replaces it in place when one already
exists (never duplicating the heading); ``read`` parses it back into a
``DesignProject``. The shared ``.herald/bridge-state.json`` (``state.py``,
AD-5) stays the *operational* source of truth CAP-3/CAP-4 read from -- this
section is the *human-readable* registry, wired in as a bootstrap fallback
only by a later story (``bridge.py``'s own docstring names that split; it
does not land here).

``readme_path`` is always an explicit ``Path`` argument, mirroring
``state.py``'s convention -- this module never assumes a cwd. Resolving a
``presentations/<slug>/README.md`` path against a real repo root is the
caller's job (Story 1.6+), not this module's; there is deliberately no
``slug`` parameter here (a README is already 1:1 with its own deck, so
nothing inside the file needs a slug key the way the shared state file's
multi-deck document does).

AD-6 governs every failure the same way it governs ``state.py``: ``register``
against a missing ``readme_path`` raises ``errors.HeraldError`` naming the
path -- this module never fabricates a whole README from nothing, only ever
edits one that already exists. ``read`` returns ``None`` for a missing file
or a missing section (mirrors ``state.py``'s "absent = None" symmetry), but
raises when the section heading is present and its body does not match the
canonical two-line shape -- a hand-edit that broke the section is corruption,
not "no section yet". Trailing blank lines at end-of-file are tolerated
(trimmed before the body is checked); a section immediately followed by
another ``#``-prefixed line is bounded correctly regardless of level.

Heading detection is an exact-string, whole-line match. A hand-edited
variant of the heading (different case, punctuation, or heading level) is
not recognized as "the section" -- ``register`` would append a second
section rather than update the mismatched one -- and content inside a
fenced code example is not distinguished from real structure either: the
literal heading text quoted in a fence reads as the section, and any other
``#``-prefixed line inside a fence bounds the section span early the same
way a real heading would. All are rare, out-of-scope hand-edit shapes: this
module's round-trip guarantee covers only its own canonical output, never
arbitrary hand-authored prose (see the story spec's "Never" boundary).

The canonical section is fixed text, matching the already-hand-seeded
pyforge-* deck READMEs' heading (only the heading; their surrounding prose
predates this module and is not this module's business to parse -- see the
module-level "Never" boundary in the story spec)::

    ## Design project (the bridge's far end)
    Prototype lives in Claude Design project **"{project_name}"** (`{project_id}`):
    {file_url}

``register`` writes atomically (temp file in the same directory as
``readme_path``, then ``os.replace``), mirroring ``state.write``'s
crash-safety pattern and its documented limit: neither fsyncs, and
concurrent writers are not addressed. The write re-serializes the whole
file with ``\n`` line endings (it parses via ``str.splitlines`` and joins
with ``\n``): a CRLF file, or an exotic line separator inside unrelated
prose, comes back normalized -- the rewrite touches every line boundary in
the file, not just the owned span.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pyforge.core.atomic_write import atomic_write_text

from . import errors

_SECTION_HEADING = "## Design project (the bridge's far end)"
"""The fixed heading text this module owns. Matched as a whole line -- an
ATX heading of any *other* level, or any other wording, is not this
section."""

_BODY_LINE1_RE = re.compile(
    r'^Prototype lives in Claude Design project \*\*"(?P<project_name>.+?)"\*\*'
    r" \(`(?P<project_id>.+?)`\):$"
)
"""Parses the canonical body's first line back into its two fields. A field
embedding the literal envelope around it (``"**`` / `` `):`` ``) would shift
the non-greedy match and parse back as the wrong fields -- ``register``
enforces the assumption by re-parsing every line it is about to write and
refusing fields that do not read back as themselves."""


@dataclass(frozen=True)
class DesignProject:
    """The three fields the § *Design project* section round-trips: the
    Claude Design project's display name, its id, and the prototype file's
    URL."""

    project_name: str
    project_id: str
    file_url: str


def _canonical_body(project_name: str, project_id: str, file_url: str) -> list[str]:
    """The section's exact two body lines, in the template ``register``
    writes and ``read`` parses back."""
    line1 = f'Prototype lives in Claude Design project **"{project_name}"** (`{project_id}`):'
    return [line1, file_url]


def _find_heading(lines: list[str], heading: str) -> int | None:
    """The index of ``heading``'s line, or ``None`` when absent.

    Only the first occurrence is considered -- ``register``/
    ``register_potx_template`` never produce more than one of their own
    heading, so a second one can only come from a hand-edit, which is
    outside this module's parsing contract (see the module docstring).
    Generalized (Story 23.3) so both the § *Design project* heading and the
    separate § *PowerPoint template* heading share one lookup."""
    for index, line in enumerate(lines):
        if line == heading:
            return index
    return None


def _section_span_end(lines: list[str], heading_index: int) -> int:
    """The index one past the section's last body line: the next
    ``#``-prefixed line (any heading level) after ``heading_index``, or
    ``len(lines)`` when none follows -- the story's own "heading line
    through the next ``#``-prefixed line or EOF" span definition."""
    for index in range(heading_index + 1, len(lines)):
        if lines[index].startswith("#"):
            return index
    return len(lines)


def register(readme_path: Path, project_name: str, project_id: str, file_url: str) -> None:
    """Append or replace the § *Design project* section in ``readme_path``.

    Against a README with no existing section, appends the canonical section
    at the end, separated from whatever content is already there by exactly
    one blank line (any trailing blank lines already at EOF are trimmed
    first, so a re-``register`` against an already-blank-terminated file
    never accumulates more than one). Against a README that already carries
    the section, replaces the span from the heading line through the next
    ``#``-prefixed line or EOF, in place -- the heading is never duplicated.
    A hand-maintained line or table directly under the section with nothing
    ``#``-prefixed after it is replaced too; that is a documented limit, not
    a silent bug (this module owns the whole span, not just what it wrote).
    When the section is followed by more content, exactly one blank line
    separates the new section from it -- the replace never glues the two
    together, regardless of how much blank-line spacing the replaced span
    itself held.

    Writes atomically: a temp file in ``readme_path``'s own directory, then
    ``os.replace`` -- mirrors ``state.write``'s crash-safety pattern and its
    limit (no fsync; concurrent writers are not addressed). Unlike
    ``state.write`` (which owns its file from birth), ``register`` edits a
    pre-existing tracked file, so the replacement preserves ``readme_path``'s
    permission bits rather than adopting ``mkstemp``'s private 0600.

    Raises ``errors.HeraldError`` naming ``readme_path`` when any of
    ``project_name``/``project_id``/``file_url`` is not a single-line,
    non-empty, UTF-8-encodable string (each becomes exactly one line of the
    canonical body -- "single-line" means every line boundary
    ``str.splitlines`` recognizes, not just ``\n``/``\r``), when
    ``file_url`` starts with ``#`` (alone on its line, it would read back
    as the heading that ends the section), when ``project_name`` or
    ``project_id`` embeds the template's own delimiters and would not parse
    back as itself (accepting any of these would write a file this module's
    own ``read`` could not faithfully parse back -- the round trip is this
    module's central promise), when the file does not exist (this module
    never fabricates a whole README), or when the filesystem otherwise
    refuses the read or the write."""
    could_not = f"design project could not be registered in {readme_path}"
    for field_name, value in (
        ("project_name", project_name),
        ("project_id", project_id),
        ("file_url", file_url),
    ):
        if not isinstance(value, str) or not value or value.splitlines() != [value]:
            raise errors.HeraldError(
                f"{could_not}: {field_name} must be a non-empty, single-line string, got {value!r}"
            )
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            # A lone surrogate (json.loads('"\ud800"') can produce one)
            # survives the line checks but would crash the UTF-8 write.
            raise errors.HeraldError(f"{could_not}: {field_name} is not encodable as UTF-8 ({exc})") from exc
    if file_url.startswith("#"):
        raise errors.HeraldError(
            f"{could_not}: file_url must not start with '#' -- the URL sits "
            f"on a line of its own, and a '#'-prefixed line would read back "
            f"as the heading that ends the section"
        )
    body = _canonical_body(project_name, project_id, file_url)
    parsed = _BODY_LINE1_RE.match(body[0])
    if parsed is None or parsed.group("project_name") != project_name or parsed.group("project_id") != project_id:
        raise errors.HeraldError(
            f"{could_not}: project_name/project_id embed the template's own "
            f"delimiters and would not read back as themselves, got "
            f"{project_name!r} / {project_id!r}"
        )
    try:
        text = readme_path.read_text(encoding="utf-8")
        original_mode = readme_path.stat().st_mode
    except FileNotFoundError as exc:
        raise errors.HeraldError(f"{could_not}: file does not exist") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.HeraldError(f"{could_not}: {exc}") from exc

    lines = text.splitlines()
    section = [_SECTION_HEADING, *body]
    heading_index = _find_heading(lines, _SECTION_HEADING)
    if heading_index is None:
        prefix = list(lines)
        while prefix and prefix[-1] == "":
            prefix.pop()
        new_lines = [*prefix, "", *section] if prefix else section
    else:
        span_end = _section_span_end(lines, heading_index)
        following = lines[span_end:]
        separator = [""] if following else []
        new_lines = [*lines[:heading_index], *section, *separator, *following]
    new_text = "\n".join(new_lines) + "\n"

    try:
        # `mode=original_mode & 0o7777` (Story 14.2, CAP-2): the shared
        # `pyforge.core.atomic_write_text` primitive's mkstemp-created temp
        # file is private (0600) by default; carrying that onto a
        # pre-existing, tracked README via `os.replace` would silently strip
        # group/other read from a file this module did not create, so the
        # `mode` chmod-before-replace preserves the ORIGINAL file's
        # permission bits instead.
        atomic_write_text(readme_path, new_text, mode=original_mode & 0o7777)
    except (OSError, ValueError) as exc:
        # The up-front UTF-8 validation makes a UnicodeEncodeError (a
        # ValueError) from the write unreachable -- wrapped anyway,
        # mirroring state.write's rationale: a raw leak through the
        # AD-6 contract is worse than a redundant guard.
        raise errors.HeraldError(f"{could_not}: {exc}") from exc


def read(readme_path: Path) -> DesignProject | None:
    """The § *Design project* section's fields, or ``None`` when
    ``readme_path`` does not exist or exists but carries no such section
    (both are "nothing registered yet", never an error).

    Raises ``errors.HeraldError`` naming ``readme_path`` when the section
    heading is present but its body does not match the canonical two-line
    shape (a hand-edit broke it -- that is corruption, not "no section"),
    or when the filesystem otherwise refuses the read."""
    try:
        text = readme_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.HeraldError(f"design project could not be read from {readme_path}: {exc}") from exc

    lines = text.splitlines()
    heading_index = _find_heading(lines, _SECTION_HEADING)
    if heading_index is None:
        return None
    span_end = _section_span_end(lines, heading_index)
    body = lines[heading_index + 1 : span_end]
    while body and body[-1] == "":
        # A section at end-of-file with no following heading pulls every
        # trailing blank line into its span (nothing bounds it otherwise);
        # those carry no information and must not count as extra body lines.
        body.pop()

    malformed = f"design project section in {readme_path} is malformed"
    if len(body) != 2:
        raise errors.HeraldError(
            f"{malformed}: expected exactly two body lines, found {len(body)} "
            f"(blank lines inside the section count as body lines; trailing "
            f"blank lines at end of file do not)"
        )
    match = _BODY_LINE1_RE.match(body[0])
    if match is None:
        raise errors.HeraldError(
            f"{malformed}: first body line does not match the canonical "
            f"'Prototype lives in Claude Design project ...' form"
        )
    return DesignProject(
        project_name=match.group("project_name"),
        project_id=match.group("project_id"),
        file_url=body[1],
    )


# --- Story 23.3: § *PowerPoint template* (the .potx path) -------------------
#
# A separate, additive registry section -- never a third line on § *Design
# project* (Design Notes: "New section, not a 3rd line on Design project"):
# that section's docstring frames itself narrowly around the Design bridge
# and hard-invariants a 2-line body; the .potx path is a repo-local build
# concern, unrelated to "the bridge's far end". `register`/`read` above are
# untouched by everything below -- only `_find_heading`'s new `heading`
# parameter (shared by both sections) touches their call sites.

_POTX_SECTION_HEADING = "## PowerPoint template (the .potx path)"
"""The fixed heading text this pair of functions owns -- matched as a
whole line, exactly like ``_SECTION_HEADING``. Single-line body: the
repo-root-relative POSIX path to the deck's ``.potx``/``.pptx`` template."""


def register_potx_template(readme_path: Path, template_path: str) -> None:
    """Append or replace the § *PowerPoint template* section in
    ``readme_path``, declaring the repo-root-relative POSIX path to a
    deck's ``.potx`` template (Story 23.3, deck_pipeline.py's
    ``select_exporter`` reads it back). Append-vs-replace and atomic-write
    shape mirror ``register`` exactly, over this section's own heading and
    a one-line body instead of ``register``'s two.

    Raises ``errors.HeraldError`` naming ``readme_path`` when
    ``template_path`` is not a non-empty, single-line, UTF-8-encodable
    string, when it starts with ``#`` (would read back as the heading that
    ends the section), when the file does not exist, or when the
    filesystem otherwise refuses the read or the write."""
    could_not = f"potx template could not be registered in {readme_path}"
    if not isinstance(template_path, str) or not template_path or template_path.splitlines() != [template_path]:
        raise errors.HeraldError(
            f"{could_not}: template_path must be a non-empty, single-line string, got {template_path!r}"
        )
    try:
        template_path.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise errors.HeraldError(f"{could_not}: template_path is not encodable as UTF-8 ({exc})") from exc
    if template_path.startswith("#"):
        raise errors.HeraldError(
            f"{could_not}: template_path must not start with '#' -- it sits "
            f"on a line of its own, and a '#'-prefixed line would read back "
            f"as the heading that ends the section"
        )
    posix_path = PurePosixPath(template_path)
    if posix_path.is_absolute() or ".." in posix_path.parts:
        raise errors.HeraldError(
            f"{could_not}: template_path must be a repo-root-relative POSIX "
            f"path with no '..' segments, got {template_path!r} -- "
            f"deck_pipeline.py's PptxTemplateExporter joins it onto "
            f"repo_root, and an absolute path silently discards repo_root "
            f"entirely"
        )

    try:
        text = readme_path.read_text(encoding="utf-8")
        original_mode = readme_path.stat().st_mode
    except FileNotFoundError as exc:
        raise errors.HeraldError(f"{could_not}: file does not exist") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.HeraldError(f"{could_not}: {exc}") from exc

    lines = text.splitlines()
    section = [_POTX_SECTION_HEADING, template_path]
    heading_index = _find_heading(lines, _POTX_SECTION_HEADING)
    if heading_index is None:
        prefix = list(lines)
        while prefix and prefix[-1] == "":
            prefix.pop()
        new_lines = [*prefix, "", *section] if prefix else section
    else:
        span_end = _section_span_end(lines, heading_index)
        following = lines[span_end:]
        separator = [""] if following else []
        new_lines = [*lines[:heading_index], *section, *separator, *following]
    new_text = "\n".join(new_lines) + "\n"

    try:
        atomic_write_text(readme_path, new_text, mode=original_mode & 0o7777)
    except (OSError, ValueError) as exc:
        raise errors.HeraldError(f"{could_not}: {exc}") from exc


def read_potx_template(readme_path: Path) -> str | None:
    """The § *PowerPoint template* section's declared path, or ``None``
    when ``readme_path`` does not exist or carries no such section (both
    are "no template declared", never an error -- the routing default).

    Raises ``errors.HeraldError`` naming ``readme_path`` when the heading
    is present but its body is not exactly one line (a hand-edit broke
    it), when that line is an absolute or ``..``-containing path (the same
    guard ``register_potx_template`` applies on write -- re-applied here
    because this section can be hand-edited directly, bypassing that
    write-time check entirely), or when the filesystem otherwise refuses
    the read."""
    try:
        text = readme_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.HeraldError(f"potx template could not be read from {readme_path}: {exc}") from exc

    lines = text.splitlines()
    heading_index = _find_heading(lines, _POTX_SECTION_HEADING)
    if heading_index is None:
        return None
    span_end = _section_span_end(lines, heading_index)
    body = lines[heading_index + 1 : span_end]
    while body and body[-1] == "":
        body.pop()

    if len(body) != 1:
        raise errors.HeraldError(
            f"potx template section in {readme_path} is malformed: expected exactly one body line, found {len(body)}"
        )
    template_path = body[0]
    posix_path = PurePosixPath(template_path)
    if posix_path.is_absolute() or ".." in posix_path.parts:
        raise errors.HeraldError(
            f"potx template section in {readme_path} is malformed: "
            f"template_path must be a repo-root-relative POSIX path with "
            f"no '..' segments, got {template_path!r} -- "
            f"deck_pipeline.py's PptxTemplateExporter joins it onto "
            f"repo_root, and an absolute path silently discards repo_root "
            f"entirely"
        )
    return template_path


# --- Story 23.4: § *Ledger* push-and-prove rows ------------------------------
#
# Unlike `register`/`register_potx_template` above -- each owning one fixed
# heading, replaced in place -- every real `## Ledger — <date> ...` section
# in a deck README (e.g. `presentations/pyforge-herald/README.md`) behaves
# like a dated changelog entry: appended once per sweep, never touched again
# by a LATER sweep. `append_push_ledger_row` follows that second, already-
# established convention instead of `register`'s replace-in-place one.

_LEDGER_TABLE_HEADER = "| Artifact | Bytes | Read-back |"
_LEDGER_TABLE_SEPARATOR = "|---|---|---|"


def _push_ledger_heading(date: str) -> str:
    """Today's own dated heading -- distinct from any other day's, so a
    second push-and-prove run on a LATER date appends a new section rather
    than folding into an old one (mirroring every hand-written dated Ledger
    section already in this repo)."""
    return f"## Ledger — {date} push-and-prove (spec-design-sync-loop CAP-6)"


def _format_ledger_row(filename: str, size: int) -> str:
    return f"| {filename} | {size:,} | identical ✓ |"


def append_push_ledger_row(readme_path: Path, *, date: str, rows: Sequence[tuple[str, int]]) -> None:
    """Append one Ledger row per ``(filename, size)`` in ``rows`` to
    ``readme_path``'s dated ``## Ledger — {date} push-and-prove
    (spec-design-sync-loop CAP-6)`` section (Story 23.4's ``herald deck push
    --prove``) -- one row per file that was both pushed and read back
    byte-identical this run (``deck_pipeline.push_exports`` never calls this
    for a skipped, conflicted, or mismatched file).

    Unlike ``register``/``register_potx_template``, this never replaces a
    section: a README with no heading for ``date`` yet gets a brand new one
    appended at the end (with its own table header + separator); a README
    that already carries today's heading (a second push-and-prove run the
    same day) gets ``rows`` appended to that same section's existing table,
    below whatever rows are already there -- the heading is written exactly
    once per date, never duplicated.

    Raises ``errors.HeraldError`` naming ``readme_path`` when ``rows`` is
    empty (an empty append is a caller bug, not "nothing to record" -- the
    caller only invokes this when it already knows at least one file
    proved), when the file does not exist (this module never fabricates a
    whole README), or when the filesystem otherwise refuses the read or the
    write."""
    could_not = f"push ledger row could not be appended to {readme_path}"
    if not rows:
        raise errors.HeraldError(f"{could_not}: no rows given")

    try:
        text = readme_path.read_text(encoding="utf-8")
        original_mode = readme_path.stat().st_mode
    except FileNotFoundError as exc:
        raise errors.HeraldError(f"{could_not}: file does not exist") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.HeraldError(f"{could_not}: {exc}") from exc

    lines = text.splitlines()
    heading = _push_ledger_heading(date)
    new_row_lines = [_format_ledger_row(filename, size) for filename, size in rows]
    heading_index = _find_heading(lines, heading)
    if heading_index is None:
        prefix = list(lines)
        while prefix and prefix[-1] == "":
            prefix.pop()
        section = [
            heading,
            "",
            _LEDGER_TABLE_HEADER,
            _LEDGER_TABLE_SEPARATOR,
            *new_row_lines,
        ]
        new_lines = [*prefix, "", *section] if prefix else section
    else:
        span_end = _section_span_end(lines, heading_index)
        body = lines[heading_index + 1 : span_end]
        while body and body[-1] == "":
            body.pop()
        following = lines[span_end:]
        separator = [""] if following else []
        new_lines = [
            *lines[:heading_index],
            heading,
            *body,
            *new_row_lines,
            *separator,
            *following,
        ]
    new_text = "\n".join(new_lines) + "\n"

    try:
        atomic_write_text(readme_path, new_text, mode=original_mode & 0o7777)
    except (OSError, ValueError) as exc:
        raise errors.HeraldError(f"{could_not}: {exc}") from exc


# --- Story 23.1: account-wide reconciliation (CAP-1) -------------------------
#
# CAP-1's account enumeration (`deck_pipeline.account_status`) classifies
# every Design project `list_projects` returns as a presentation (with or
# without a local twin -- resolved against every deck's own § *Design
# project* section, `read`, above), a design system (a bound library, never
# a deck), or excluded (by name, with a recorded reason). Both non-
# presentation classifications are exact-identity lookups against a small,
# explicit list -- never a heuristic (the story's own Never boundary): a
# project named e.g. "REMOVED-PyForge Unifying Strategy Deck" (one word
# added) reads as an ordinary, untwinned presentation rather than silently
# matching the retired "REMOVED-PyForge Unifying Strategy" by prefix or
# substring.

DESIGN_SYSTEM_PROJECT_NAMES = frozenset({"Modernist", "Broadsheet", "Nocturne"})
"""Every Design project that is a bound design-system library, not a deck
(the operator's Q1 scope ruling, `docs/dreams/design-sync-loop.md`): mirrored
as libraries (Story 23.2), never given a deck twin, ledger or Pages page.
Matched by exact `list_projects` `name` -- the same "excluded by name, never
a heuristic" discipline `read_exclusions` below applies. Modernist is also
the deck family's own `MODERNIST_DESIGN_SYSTEM_ID` (`transport/base.py`);
recorded here by name, like its two siblings, since classification only ever
sees a live project's name, never its id, until `account_status` has already
resolved which local twin (if any) an id belongs to."""

_EXCLUDED_SECTION_HEADING = "## Excluded projects (never twinned)"
"""The fixed heading text this pair of functions owns, in
`presentations/README.md` -- the family-level registry, distinct from a
single deck's own README (which never carries this section)."""

_EXCLUDED_TABLE_HEADER = "| Project | Reason |"
_EXCLUDED_TABLE_SEPARATOR = "|---|---|"


def read_exclusions(readme_path: Path) -> dict[str, str]:
    """Every Design project name intentionally excluded from the twin-per-
    deck loop, mapped to its recorded reason (Story 23.1, CAP-1) --
    `presentations/README.md`'s own `_EXCLUDED_SECTION_HEADING` table.

    Returns `{}` when `readme_path` does not exist or carries no such
    section (both are "nothing excluded yet"). A live account project is
    excluded by an *exact* match against this table's `Project` column --
    never a name heuristic (the story's own Never boundary): the two
    projects the story names, `REMOVED-PyForge Unifying Strategy` and
    `Local recipes repository connection`, are recorded here verbatim with
    their reasons, rather than inferred from a `REMOVED-` prefix or a
    `repository connection` substring.

    Raises `errors.HeraldError` naming `readme_path` when the heading is
    present but a row under it does not match the table's two-cell
    `| Project | Reason |` shape, when a `Project` value repeats (a
    duplicate row would otherwise silently discard the earlier row's
    `reason` with no error), or when the filesystem otherwise refuses the
    read."""
    try:
        text = readme_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        raise errors.HeraldError(f"excluded-projects list could not be read from {readme_path}: {exc}") from exc

    lines = text.splitlines()
    heading_index = _find_heading(lines, _EXCLUDED_SECTION_HEADING)
    if heading_index is None:
        return {}
    span_end = _section_span_end(lines, heading_index)
    body = lines[heading_index + 1 : span_end]

    exclusions: dict[str, str] = {}
    for line in body:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if stripped in (_EXCLUDED_TABLE_HEADER, _EXCLUDED_TABLE_SEPARATOR):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 2 or not cells[0]:
            raise errors.HeraldError(
                f"excluded-projects list in {readme_path} is malformed: row "
                f"{line!r} is not a two-cell '| Project | Reason |' row"
            )
        project, reason = cells
        if project in exclusions:
            raise errors.HeraldError(
                f"excluded-projects list in {readme_path} is malformed: project {project!r} appears more than once"
            )
        exclusions[project] = reason
    return exclusions
