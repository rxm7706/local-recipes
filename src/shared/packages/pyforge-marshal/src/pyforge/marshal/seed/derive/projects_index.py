"""``seed/derive/projects_index.py`` -- derives ``_bmad-output/PROJECTS.md``'s
Projects table from the set of live projects, and manages the two BMAD
artifact symlinks that track the active project (Story 11.2).

**The gap this closes.** `_bmad-output/PROJECTS.md`'s Projects table has
always been 100% hand-maintained prose -- no region marker exists in it
until this story -- so it silently goes stale as projects are added or
removed: the exact class of drift that produced the ten-hour marker/symlink
desync incident CLAUDE.md documents (2026-07-14). Separately, nothing in
this codebase has ever CREATED or VERIFIED the two BMAD artifact symlinks
(``_bmad-output/planning-artifacts``/``implementation-artifacts``) --
``scripts/bmad-switch`` re-points them on every ``bmad-switch <slug>`` call,
but nothing ensures they exist (or agree with the marker) outside of that
one script. This module is the derive-layer content for both: ``derive_
projects_table`` computes the Projects table's body (wired into
``verbs.adopt._default_commit``'s ``projects-table`` region, see that
module's own docstring for the dispatch), and ``resolve_active_project``/
``ensure_symlinks``/``detect_symlink_desync`` are the active-project
resolution and symlink-management primitives a future caller (a
``marshal seed check``-integration story, explicitly OUT of this story's own
scope -- see the Never bullet below) can build on.

**Layering: why ``SymlinkDesync`` is a local, frozen dataclass, never a
``detect.findings.Finding``.** The architecture's module-dependency rules
place ``derive`` BELOW ``detect`` (``verbs -> (detect, plan, apply, migrate)
-> (model, state, regions, engine, derive) -> fs``, no upward imports) --
importing ``detect.findings.Finding`` from this module would itself violate
that rule. ``seed/errors.py`` has no suitable existing shape either (only
the closed, six-leaf ``SeedError`` exit-code hierarchy, which is a CLI-facing
taxonomy, not a per-artifact conformance-problem shape). A future ``detect``-
layer story can wrap a ``SymlinkDesync`` in a real ``Finding`` once desync
detection is wired into ``marshal seed check`` -- this story does not do
that wiring (see the Never bullet).

**Why ``tomllib``, not a third-party TOML library.** Mirrors ``_bmad/
scripts/resolve_config.py``'s own approach -- the stdlib parser, no new
dependency, matching every other ``.toml``-reading module in this package
(``cli/config.py``, ``cli/spin.py``, ``cli/init.py``).

**Active-project resolution never diverges from ``resolve_config.py``.**
``resolve_active_project`` reproduces that script's EXACT precedence
(``--project`` param, if supplied -> ``BMAD_ACTIVE_PROJECT`` env var ->
``_bmad/custom/.active-project`` marker file) rather than importing or
subprocessing it (that script is a standalone CLI tool, not an importable
library, and has no stable Python API to import) -- this module's own
Boundaries forbid inventing a second resolution order, so the precedence
itself must never drift from the one true source. What this module adds ON
TOP of that precedence -- stripping every source consistently, treating a
blank value as absent, and validating the final resolved value against a
slug charset -- is new, additional defensiveness this story's own review
passes required (see ``resolve_active_project``'s own docstring), not a
divergence in the precedence itself.

**Inherited limitation (review finding, pass 2): this closes the drift gap
for exactly one ``adopt`` run, not permanently.** ``detect/inventory.py``'s
existing (unchanged by this story) ``_classify_hybrid`` treats a hybrid
region as conformant purely by MARKER PRESENCE, never by content -- so once
``projects-table`` is inserted once, a later ``adopt``/``check`` will not
notice the set of live projects has changed and will not re-derive it. No
``update``/``refresh`` verb exists yet in this package to force one. This is
a pre-existing S-9.3 architectural characteristic shared by every
``hybrid-managed-region`` entry, not something specific to (or newly
introduced by) ``projects-table`` -- documented here so this module's own
"stops it going stale" framing is not read as an unqualified, permanent
guarantee.

**Never (this story's own scope boundary):** wiring ``detect_symlink_
desync`` into ``marshal seed check``'s live output is explicitly OUT of
scope -- Story 11.2's Surface per ``epics.md`` is this module (plus the
minimal ``verbs/adopt.py`` dispatch hook the table-derivation gap requires,
since ``verbs/adopt.py``'s existing dispatch ALREADY calls into the
``projects-index`` entry on every real ``adopt``/``check`` call, so leaving
that one gap unwired would ship active, wrong production behavior). Nothing
anywhere calls ``detect_symlink_desync``/``ensure_symlinks`` today, so
leaving THEM unwired is inert, not wrong -- ``verbs/check.py`` integration is
a future story's job. The functions must exist, be correct, and be tested;
they do not need a live caller yet. This also covers the manifest's own
pre-existing ``planning-artifacts-symlink``/``implementation-artifacts-
symlink`` entries (``generated-derived``, unchanged by this story): they
have no dispatch hook into ``ensure_symlinks`` either, for the identical
reason -- nothing currently schedules an ``Action`` for either id (review
finding, pass 2), so this is the SAME class of not-yet-wired, not
actively-wrong gap as the ``check`` integration above, left for the same
future story."""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .. import fs
from ..errors import PreconditionFailure

# The two BMAD artifact symlinks every active project must have, and the
# expected trailing path segment ("projects/<slug>/<name>") a symlink's
# target must carry for its slug to be treated as meaningful -- shared by
# ``ensure_symlinks`` (which creates them) and ``detect_symlink_desync``
# (which reads them back), so the two can never name the pair differently.
_ARTIFACT_LINKS: tuple[str, ...] = ("planning-artifacts", "implementation-artifacts")

# The active-project slug charset (Task (b)): lowercase, starts with a
# letter, then alnum/hyphen -- matches every real project slug in this repo
# (`pyforge-marshal`, `pyforge-atlas`, ...). Deliberately narrower than
# `resolve_config.py`'s own `_SLUG_PATTERN` (which also allows a leading
# digit and underscores): that script accepts a slightly wider wire shape,
# but this module's own validation is ADDITIONAL defensiveness on top of the
# same precedence (see the module docstring), not a re-derivation of it, and
# a real slug here is never digit-led or underscored.
_ACTIVE_PROJECT_SLUG_PATTERN = re.compile(r"[a-z][a-z0-9-]*", re.ASCII)


# --- derive_projects_table ---------------------------------------------


def _escape_cell(value: str) -> str:
    """One markdown table cell, safe to splice into a ``| ... | ... |``
    row: every literal ``|`` is escaped to ``\\|`` (markdown's own escape
    for a pipe inside a table cell, so an unescaped one can never be
    mistaken for a column boundary), every ``\\r\\n``/``\\r``/``\\n`` is
    replaced with a single space -- never dropped outright, which could
    silently splice two unrelated words together (e.g. a multi-line
    description's ``"first.\\nsecond"`` becoming the unreadable
    ``"first.second"`` instead of ``"first. second"``) -- and every literal
    backtick is escaped to ``\\``` (review finding, pass 2: the slug column
    wraps its value in a markdown code span, ```` `{slug}` ````, so an
    unescaped backtick would prematurely close that span). This is the ONE
    uniform escaping rule this module applies to every column (slug,
    status, AND description) -- a malformed value in any of them must never
    be able to corrupt the table's row/column structure."""
    return value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").replace("|", "\\|").replace("`", "\\`")


def _project_row(project_dir: Path) -> tuple[str, str, str] | None:
    """The ``(slug, status, description)`` row for one
    ``<project_dir>/.bmad-config.toml``, or ``None`` when the file is
    absent or fails to parse as TOML -- a project directory with no
    readable config simply contributes no row, rather than crashing the
    whole table derivation over one malformed entry.

    A file that DOES parse as valid TOML but carries no ``[project]``
    table (or a non-table ``project`` value) is NOT one of those "absent or
    fails to parse" cases -- it still contributes a row, falling back to
    ``project_dir.name`` for ``slug`` and an empty string for ``status``/
    ``description`` (docstring correction, review finding pass 2: an
    earlier draft of this docstring's wording implied this case also
    contributed no row, which the code never actually did)."""
    config_path = project_dir / ".bmad-config.toml"
    if not config_path.is_file():
        return None
    try:
        with config_path.open("rb") as handle:
            document = tomllib.load(handle)
    except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError:
        return None
    project_table = document.get("project") if isinstance(document, dict) else None
    if not isinstance(project_table, dict):
        project_table = {}
    slug = str(project_table.get("slug") or project_dir.name)
    status = str(project_table.get("status") or "")
    description = str(project_table.get("description") or "")
    return (slug, status, description)


def derive_projects_table(projects_dir: Path) -> str:
    """The Projects table's body -- a markdown table with one row per
    ``<projects_dir>/*/.bmad-config.toml`` file present, sorted
    deterministically by slug.

    ``projects_dir`` names ``_bmad-output/projects`` (or a synthetic
    fixture equivalent under a test's own ``tmp_path``) -- a missing
    directory, or a directory with zero project subdirectories, both
    produce the header-only table (no crash): the I/O matrix's own
    "zero `.bmad-config.toml` files" row. Every cell of every column is
    escaped via ``_escape_cell`` before rendering (see that function's own
    docstring) -- no malformed TOML value can corrupt the table's structure.

    A directory-listing failure (e.g. a permission error on ``projects_dir``
    itself) is treated the same as a missing directory -- the header-only
    table, never a crash (review finding, pass 2: an earlier draft only
    guarded the "directory doesn't exist" case, not "exists but cannot be
    listed").

    Two project directories that resolve to the SAME slug (a typo'd
    ``[project].slug`` colliding with another directory's name, or with
    another directory's own declared slug) raise ``PreconditionFailure``
    naming both directories and the shared slug, rather than silently
    rendering two identical-looking rows -- matching this package's
    established "ambiguity is refused loudly" convention elsewhere
    (``_read_region_fragment``'s/``derive.adapters._read_fragment``'s own
    identical refusal for an ambiguous fragment match; review finding,
    pass 2).

    This function never writes anything and never touches ``fs`` -- it
    returns a plain ``str``, the region BODY ``verbs.adopt._default_commit``
    splices into ``_bmad-output/PROJECTS.md`` via the real ``regions.apply.
    insert_region``/``substitute_region`` machinery (see that module's own
    docstring for the dispatch)."""
    rows: list[tuple[str, str, str]] = []
    seen_slugs: dict[str, Path] = {}
    if projects_dir.is_dir():
        try:
            project_dirs = sorted(projects_dir.iterdir(), key=lambda candidate: candidate.name)
        except OSError:
            project_dirs = []
        for project_dir in project_dirs:
            if not project_dir.is_dir():
                continue
            row = _project_row(project_dir)
            if row is None:
                continue
            slug = row[0]
            if slug in seen_slugs:
                raise PreconditionFailure(
                    f"duplicate project slug {slug!r}: both {seen_slugs[slug]} and {project_dir} resolve to it",
                    remedy=(
                        "give each project directory's .bmad-config.toml a distinct"
                        " [project].slug (or rename the directory)"
                    ),
                )
            seen_slugs[slug] = project_dir
            rows.append(row)
    rows.sort(key=lambda row: row[0])

    lines = ["| Slug | Status | Description |", "|------|--------|-------------|"]
    for slug, status, description in rows:
        lines.append(f"| `{_escape_cell(slug)}` | {_escape_cell(status)} | {_escape_cell(description)} |")
    return "\n".join(lines) + "\n"


# --- resolve_active_project ---------------------------------------------


def _validate_slug(value: str, *, source: str) -> str:
    """``value``, unchanged, if it matches ``_ACTIVE_PROJECT_SLUG_PATTERN``;
    otherwise raises ``PreconditionFailure`` naming ``value`` and
    ``source``. The single validation choke point every resolved candidate
    -- and the synthesized "nothing resolved" empty-value case -- routes
    through, so every invalid shape (empty, absolute-path-shaped,
    ``..``-containing, or otherwise outside the charset) is reported with
    the identical named-error shape, never a second, independently-worded
    message."""
    if _ACTIVE_PROJECT_SLUG_PATTERN.fullmatch(value) is None:
        raise PreconditionFailure(
            f"invalid active-project slug {value!r} from {source} -- expected to match"
            f" {_ACTIVE_PROJECT_SLUG_PATTERN.pattern!r} (lowercase, starting with a"
            " letter, then alphanumeric/hyphen only -- this also rejects an"
            " absolute-path-shaped or '..'-containing value, since neither '/' nor '.'"
            " is in the allowed charset)",
            remedy=(
                "fix the value at its source (the --project flag, the BMAD_ACTIVE_PROJECT"
                " env var, or _bmad/custom/.active-project), or pass a valid slug explicitly"
            ),
        )
    return value


def resolve_active_project(repo_root: Path, *, project: str | None = None) -> str:
    """The active project's slug, resolved via ``resolve_config.py``'s own,
    unmodified precedence: ``project`` (this function's own ``--project``-
    equivalent parameter) -> the ``BMAD_ACTIVE_PROJECT`` environment
    variable -> the ``_bmad/custom/.active-project`` marker file under
    ``repo_root``.

    Every source is stripped consistently (not just the marker -- Task (b)'s
    own review finding: an earlier draft stripped only the marker file,
    leaving a padded env var or ``--project`` value to slip through
    unstripped) and a blank (empty or whitespace-only) value from ANY source
    is treated as absent, falling through to the next source exactly like a
    genuinely-missing one -- ``resolve_config.py``'s own behavior for the
    marker file, generalized here to every source.

    Once a non-blank candidate is found, it is validated against
    ``_ACTIVE_PROJECT_SLUG_PATTERN`` (Task (b)) before being returned:
    an invalid shape (empty after all sources are exhausted,
    absolute-path-shaped, ``..``-containing, or otherwise outside the
    charset) raises ``PreconditionFailure`` naming the offending value and
    its source -- never a bare, unhandled exception, and never a silently
    malformed value threaded through to become a broken symlink target
    later. When EVERY source is absent or blank, this is reported as an
    empty value from a synthesized "no source" locator, through the exact
    same validation path (rather than a second, differently-worded error) --
    unlike ``resolve_config.py`` itself, which legitimately returns ``None``
    for "no active project resolves" (a normal state for that script's
    OWN callers), this function's return type is a plain ``str``: it exists
    to feed ``ensure_symlinks``, for which "no active project" is not a
    value that can usefully continue."""
    marker_path = repo_root / "_bmad" / "custom" / ".active-project"
    marker_value: str | None = None
    if marker_path.is_file():
        try:
            marker_value = marker_path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            # An unreadable or non-UTF-8 marker is treated the same as a
            # missing one (falls through to the next source, or the final
            # "no source" report) -- never an uncaught exception (review
            # finding, pass 2).
            marker_value = None

    candidates: tuple[tuple[str, str | None], ...] = (
        ("--project", project),
        ("BMAD_ACTIVE_PROJECT env var", os.environ.get("BMAD_ACTIVE_PROJECT")),
        (str(marker_path), marker_value),
    )

    for source, raw_value in candidates:
        if raw_value is None:
            continue
        stripped = raw_value.strip()
        if not stripped:
            continue
        return _validate_slug(stripped, source=source)

    # Every source was absent or blank -- routed through the SAME validator
    # (an empty string never matches `_ACTIVE_PROJECT_SLUG_PATTERN`) so this
    # is reported with the identical named-error shape as a malformed value,
    # not a second, independently-worded message.
    return _validate_slug(
        "",
        source=(f"no source (--project, BMAD_ACTIVE_PROJECT, and {marker_path} were all absent or blank)"),
    )


# --- ensure_symlinks ------------------------------------------------------


def ensure_symlinks(repo_root: Path, active_slug: str, *, never_write: fs.NeverWrite) -> None:
    """Ensure both BMAD artifact symlinks under ``repo_root/_bmad-output/``
    exist and point at ``active_slug``'s own ``planning-artifacts``/
    ``implementation-artifacts`` directories, via the guarded ``fs.symlink``
    primitive.

    ``active_slug`` is assumed to have already passed ``resolve_active_
    project``'s own charset validation (this function deliberately does NOT
    re-derive that check -- Task (c)) -- but since this function's own
    signature makes ``active_slug`` a directly-callable parameter, not only
    reachable via ``resolve_active_project``, it DOES defensively reject an
    empty or whitespace-only value with a clear, named error rather than
    silently building a symlink target out of it.

    Before calling ``fs.symlink`` for either link, verifies the computed
    target directory (``_bmad-output/projects/<active_slug>/planning-
    artifacts``/``implementation-artifacts``) actually exists, raising
    ``PreconditionFailure`` naming the missing directory if not -- never
    silently creating a dangling symlink. The target passed to ``fs.symlink``
    itself is the RELATIVE form ``projects/<active_slug>/<name>`` (relative
    to ``_bmad-output/``, the symlink's own parent directory) -- mirroring
    ``scripts/bmad-switch::repoint_links``'s own, already-incident-tested
    convention exactly, rather than inventing an absolute-path spelling."""
    if not isinstance(active_slug, str) or not active_slug.strip():
        raise PreconditionFailure(
            f"active_slug must be a non-empty, non-blank str, got {active_slug!r}",
            remedy="pass a slug already validated by resolve_active_project",
        )

    for name in _ARTIFACT_LINKS:
        target_dir = repo_root / "_bmad-output" / "projects" / active_slug / name
        if not target_dir.is_dir():
            raise PreconditionFailure(
                f"symlink target does not exist: {target_dir}",
                remedy=(
                    f"create {target_dir} (e.g. via `marshal seed adopt`/`init`, or by hand)"
                    " before ensuring the artifact symlinks"
                ),
            )

    completed: list[str] = []
    for name in _ARTIFACT_LINKS:
        link_path = repo_root / "_bmad-output" / name
        target = Path("projects") / active_slug / name
        try:
            fs.symlink(link_path, target, repo_root=repo_root, never_write=never_write)
        except Exception as exc:
            # Never auto-repair (this module's own Never bullet), so this is
            # NOT a rollback of `completed` -- just a diagnostic naming
            # exactly what state the repo is now in, so the caller (or a
            # human) knows to run `detect_symlink_desync` rather than
            # discover a half-migrated pair by surprise later (review
            # finding, pass 2: an earlier draft let the second call's own
            # exception propagate unchanged, with no indication the first
            # symlink had already changed).
            raise PreconditionFailure(
                f"created/updated {completed!r} before failing on {name!r}: {exc}",
                remedy=(
                    "the artifact symlinks may now be inconsistent -- run"
                    " detect_symlink_desync to check, then re-run ensure_symlinks once"
                    " the underlying failure is fixed"
                ),
            ) from exc
        completed.append(name)


# --- detect_symlink_desync ------------------------------------------------


@dataclass(frozen=True)
class SymlinkDesync:
    """A HARD finding: the active-project marker and the two BMAD artifact
    symlinks (``planning-artifacts``/``implementation-artifacts``) disagree
    about which project is active. Names every disagreeing value -- never a
    bare boolean -- so a human reader never has to re-derive what
    mismatched, the exact failure mode CLAUDE.md's own marker/symlink
    desync incident (2026-07-14) documents.

    A local, frozen dataclass, NOT a ``detect.findings.Finding`` -- see the
    module docstring's own layering rationale. ``planning_artifacts_project``/
    ``implementation_artifacts_project`` carry either a real slug (parsed
    from that symlink's own target) or an ``"<unrecognized-target-shape:
    ...>"``/``"<absent-or-not-a-symlink: ...>"`` sentinel string when the
    target's shape could not be interpreted as ``projects/<slug>/<name>`` --
    a sentinel never collides with a real slug (no real slug contains
    ``<``), so it is always treated as disagreeing with the marker, never
    silently coerced into agreement."""

    marker_project: str
    planning_artifacts_project: str
    implementation_artifacts_project: str


def _parsed_symlink_project(raw_target: str, artifact_name: str) -> str:
    """The project slug a symlink's raw, literal target string names, or an
    ``"<unrecognized-target-shape: ...>"`` sentinel when it does not.

    Parses ``raw_target`` via ``Path(...).parts`` -- pure text, no
    filesystem access -- which handles a RELATIVE target
    (``projects/<slug>/<name>``, this module's own ``ensure_symlinks``
    convention) and an ABSOLUTE target (e.g.
    ``/abs/repo/_bmad-output/projects/<slug>/<name>``) uniformly: both
    shapes end in the same three trailing segments, so checking from the
    END of ``parts`` (rather than requiring an exact total length, the way
    ``scripts/bmad-switch::read_link_slugs`` does for its own narrower,
    relative-only case) is what lets an absolute-path target resolve
    correctly instead of being rejected as unparseable (Task (d)'s own
    review finding). The target's FINAL path segment must equal
    ``artifact_name`` (``planning-artifacts`` or ``implementation-
    artifacts``) before the segment before it is ever treated as a
    meaningful slug -- otherwise a target that happens to end in some other
    directory name is correctly reported as unrecognized rather than
    silently misread."""
    parts = Path(raw_target).parts
    if len(parts) >= 3 and parts[-1] == artifact_name and parts[-3] == "projects":
        return parts[-2]
    return f"<unrecognized-target-shape: {raw_target!r}>"


def _symlink_project(repo_root: Path, artifact_name: str) -> str:
    link_path = repo_root / "_bmad-output" / artifact_name
    if not link_path.is_symlink():
        return f"<absent-or-not-a-symlink: {link_path}>"
    return _parsed_symlink_project(os.readlink(link_path), artifact_name)


def detect_symlink_desync(repo_root: Path, marker_project: str) -> SymlinkDesync | None:
    """``None`` when both BMAD artifact symlinks under
    ``repo_root/_bmad-output/`` agree with ``marker_project``, else a
    ``SymlinkDesync`` naming every disagreeing value.

    Reads each symlink's raw target via ``os.readlink`` and parses it with
    ``_parsed_symlink_project`` -- text-only parsing, so an absolute-path
    target that legitimately resolves to the correct project is compared
    correctly (never rejected as a parse failure, and never falsely flagged
    as desync just for being spelled absolutely) while a target whose shape
    genuinely does not match ``projects/<slug>/<name>`` is its own distinct,
    always-disagreeing "unrecognized shape" condition (Task (d)) -- never
    silently coerced into agreement with ``marker_project`` merely because
    string comparison did not raise.

    This function performs no filesystem WRITE and never touches ``fs`` --
    read-only detection only. Nothing in this package calls it yet (see the
    module docstring's own Never bullet); it is complete and independently
    tested, awaiting a future ``marshal seed check`` integration story."""
    planning = _symlink_project(repo_root, "planning-artifacts")
    implementation = _symlink_project(repo_root, "implementation-artifacts")
    if planning == marker_project and implementation == marker_project:
        return None
    return SymlinkDesync(
        marker_project=marker_project,
        planning_artifacts_project=planning,
        implementation_artifacts_project=implementation,
    )
