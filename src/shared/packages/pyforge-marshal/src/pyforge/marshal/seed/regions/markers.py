"""Marker grammar and the per-format comment registry (Story 8.1,
architecture AD-53).

AD-53 fixes ONE marker grammar, rendered through a per-format comment
syntax chosen ONLY from an artifact's declared ``format`` -- never sniffed
from a file's content or extension (this story's own Always bullet):

.. code-block:: text

    <open> marshal-seed:begin region=<name> model-version=<semver> sha=<8-hex> <close>
    <open> marshal-seed:end region=<name> <close>

Story 7.4's ``seed/model/manifest.py`` shipped the manifest loader with two
forward-referenced checks deliberately left unenforced -- its own Review
Triage Log names this story as the one that closes them: a
``hybrid-managed-region`` entry's ``format`` was accepted as any non-blank
string, and a ``Region.name`` was accepted as any non-blank string. Both
gaps close here: this module is the registry ``manifest.py`` validates
``format`` against, and ``REGION_NAME_PATTERN`` is exported so
``manifest.py`` validates ``name`` with the exact same rule this module
enforces on ``BeginMarker``/``EndMarker`` -- one charset, checked in both
places, never two independently-drifting regexes.

Registry v1 has three members (``RegionFormat``): ``html`` (``<!-- ... -->``,
for ``.md``), ``hash`` (``# ...`` -- deliberately no closing delimiter, for
``.gitignore``/``.toml``/``.yml``/``.yaml``/shell), and ``slashstar``
(``/* ... */``) -- registered as a real enum member (so a manifest may
legally declare it, and a future story can implement it without a schema
migration) but both ``render_begin``/``render_end`` and ``parse_marker_line``
raise ``NotImplementedError`` the moment it is selected, per this story's
own Always bullet: no ``.c``/``.js``/... artifact is seeded in V1, so
shipping an untested rendering for it would be the exact kind of
speculative surface ``Simplicity First`` forbids.

``region_sha`` hashes the region BODY only -- never the marker line itself
-- so the marker is provably not self-referential: renaming a region or
bumping its ``model-version`` never changes the sha, only the body's own
content does.

This module owns line-level grammar only. It does NOT scan a file for
marker spans, reject nesting/overlap, resolve the ``<top>`` anchor
sentinel, perform span substitution, or normalize CRLF/LF -- all later,
separate stories (S-8.2 through S-8.5, this story's own Never bullets).
``parse_marker_line`` only GUARANTEES recognition of the EXACT canonical
grammar ``render_begin``/``render_end`` emit. A line that carries the
``marshal-seed:`` tag but varies from that exact shape (irregular
whitespace, a CRLF ending) is unspecified here -- depending on exactly
where the variance falls, it may read as ordinary content (``None``) or as
a malformed marker (``MarkerError``); this module makes no promise about
which. Recovering that variance predictably is S-8.2's job, once it
re-normalizes a file before consulting this grammar.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum

from pyforge.core.errors import PyforgeError

from ..model.version import InvalidVersionError, ModelVersion

# The marker-safe region-name token: lowercase alnum, optionally followed by
# more lowercase alnum or hyphens -- no raw space or `=`, since both are
# grammar-significant in the marker line itself (` region=<name> ` would be
# ambiguous the moment `<name>` could contain either). Matches every region
# name already in `templates/manifest.yaml` (`tiers`,
# `portability-contract`, `dream-first-workflow`, `model-ignores`,
# `model-badge`, `bmad-multiproject`). Public: `seed/model/manifest.py`
# reuses this exact object for `Region.name`, so the two validators can
# never drift into two different charsets for the same identity.
#
# No ^/$ anchors -- matched with `.fullmatch()`, not `.match()`, per
# `seed/model/version.py`'s own documented convention (a `$`-anchored
# pattern alone matches immediately before a trailing "\n", which would let
# a name like "tiers\n" slip past this check).
REGION_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*", re.ASCII)

# Exactly 8 lowercase hex characters -- `region_sha`'s own output shape.
# `re.ASCII` for the same reason `version.py` uses it on every grammar
# pattern in this package: without it, Python's bare character classes also
# match non-ASCII Unicode digit forms.
_SHA_PATTERN = re.compile(r"[0-9a-f]{8}", re.ASCII)

_MARKER_TAG = "marshal-seed"
_MARKER_TAG_RE = re.escape(_MARKER_TAG)
_BEGIN_BODY_PATTERN = re.compile(
    rf"{_MARKER_TAG_RE}:begin region=(?P<region>\S+)"
    r" model-version=(?P<model_version>\S+) sha=(?P<sha>\S+)",
    re.ASCII,
)
_END_BODY_PATTERN = re.compile(rf"{_MARKER_TAG_RE}:end region=(?P<region>\S+)", re.ASCII)


class RegionFormat(StrEnum):
    """The per-format comment-style registry, v1 (AD-53). Selected only
    from an artifact's declared ``format`` -- never sniffed."""

    HTML = "html"
    HASH = "hash"
    SLASHSTAR = "slashstar"


class MarkerError(PyforgeError, ValueError):
    """Story 14.3, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``ValueError`` stays in the MRO.

    Raised for any marker-grammar violation: a region name outside
    ``REGION_NAME_PATTERN``, a sha that is not exactly 8 lowercase hex
    characters, a ``model-version`` field that does not parse as a
    ``ModelVersion``, or a line that carries the ``marshal-seed:`` tag but
    does not otherwise match the grammar. Never raised for an ordinary,
    non-marker line -- ``parse_marker_line`` returns ``None`` for those.
    """


# Per-format delimiters: (open, close). `close` is `None` for `hash`,
# whose `#` comment already runs to end of line -- AD-53's registry
# deliberately gives it no closing token, matching every hash-comment
# language already in the registry (`.gitignore`/`.toml`/`.yml`/`.yaml`/
# shell). `slashstar` carries real delimiters here (so the registry entry
# is complete, forward-compatible data) even though `render_*`/
# `parse_marker_line` never reach them -- both raise `NotImplementedError`
# before consulting this table.
_DELIMITERS: dict[RegionFormat, tuple[str, str | None]] = {
    RegionFormat.HTML: ("<!--", "-->"),
    RegionFormat.HASH: ("#", None),
    RegionFormat.SLASHSTAR: ("/*", "*/"),
}


def _coerce_format(fmt: RegionFormat) -> RegionFormat:
    """Normalize ``fmt`` to its canonical ``RegionFormat`` singleton.

    A type-correct caller already passes a real ``RegionFormat`` member, for
    which this is a no-op (``RegionFormat(member) is member``). Without this,
    a caller that instead passes the bare string ``"slashstar"`` (matching by
    value, not identity) would skip the ``is RegionFormat.SLASHSTAR`` guard
    below -- StrEnum's dict-key hashing makes ``_DELIMITERS["slashstar"]``
    resolve too, so the unimplemented format would silently render/parse
    instead of raising. Raises ``MarkerError`` (not a bare ``ValueError`` or
    ``KeyError``) for any value outside the three-member registry, matching
    every other grammar violation this module reports."""
    try:
        return RegionFormat(fmt)
    except ValueError as exc:
        raise MarkerError(f"fmt must be a registered RegionFormat, got {fmt!r}") from exc


def _require_region_name(value: object) -> str:
    if not isinstance(value, str) or REGION_NAME_PATTERN.fullmatch(value) is None:
        raise MarkerError(
            f"region name must match {REGION_NAME_PATTERN.pattern!r}"
            f" (marker-safe token: lowercase alnum, then alnum/hyphen), got {value!r}"
        )
    return value


@dataclass(frozen=True)
class EndMarker:
    """A parsed/constructed ``marshal-seed:end`` marker."""

    region: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "region", _require_region_name(self.region))


@dataclass(frozen=True)
class BeginMarker:
    """A parsed/constructed ``marshal-seed:begin`` marker."""

    region: str
    model_version: ModelVersion
    sha: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "region", _require_region_name(self.region))
        if not isinstance(self.model_version, ModelVersion):
            raise MarkerError(f"model_version must be a ModelVersion, got {self.model_version!r}")
        if not isinstance(self.sha, str) or _SHA_PATTERN.fullmatch(self.sha) is None:
            raise MarkerError(f"sha must be exactly 8 lowercase hex characters, got {self.sha!r}")


def region_sha(body: str) -> str:
    """The region body's sha, truncated to 8 hex characters -- matching
    this repo's existing truncated-sha256 idiom (e.g.
    ``pyforge.warden.actuator``). Hashes the body ONLY: the marker line
    that carries this value is therefore never self-referential -- renaming
    the region or bumping its ``model-version`` alone (body unchanged)
    never changes the result."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:8]


def _render(fmt: RegionFormat, body: str) -> str:
    open_token, close_token = _DELIMITERS[fmt]
    if close_token is None:
        return f"{open_token} {body}"
    return f"{open_token} {body} {close_token}"


def render_begin(fmt: RegionFormat, region: str, model_version: ModelVersion, sha: str) -> str:
    """Render a ``marshal-seed:begin`` marker line in ``fmt``'s comment
    style. Raises ``NotImplementedError`` for ``RegionFormat.SLASHSTAR``
    (reserved, unimplemented in V1) and ``MarkerError`` for a
    grammar-violating ``region``/``model_version``/``sha``."""
    fmt = _coerce_format(fmt)
    if fmt is RegionFormat.SLASHSTAR:
        raise NotImplementedError("RegionFormat.SLASHSTAR is reserved, unimplemented in V1")
    marker = BeginMarker(region=region, model_version=model_version, sha=sha)
    body = f"{_MARKER_TAG}:begin region={marker.region} model-version={marker.model_version} sha={marker.sha}"
    return _render(fmt, body)


def render_end(fmt: RegionFormat, region: str) -> str:
    """Render a ``marshal-seed:end`` marker line in ``fmt``'s comment
    style. Raises ``NotImplementedError`` for ``RegionFormat.SLASHSTAR``
    (reserved, unimplemented in V1) and ``MarkerError`` for a
    grammar-violating ``region``."""
    fmt = _coerce_format(fmt)
    if fmt is RegionFormat.SLASHSTAR:
        raise NotImplementedError("RegionFormat.SLASHSTAR is reserved, unimplemented in V1")
    marker = EndMarker(region=region)
    body = f"{_MARKER_TAG}:end region={marker.region}"
    return _render(fmt, body)


def _strip_delimiters(fmt: RegionFormat, line: str) -> str | None:
    """Return the text between ``fmt``'s delimiters, or ``None`` if
    ``line`` does not open (and, when the format has one, close) with
    them at all -- i.e. it is not a candidate marker line in this format,
    ordinary content."""
    open_token, close_token = _DELIMITERS[fmt]
    text = line.rstrip("\n")
    prefix = f"{open_token} "
    if not text.startswith(prefix):
        return None
    remainder = text[len(prefix) :]
    if close_token is None:
        return remainder
    suffix = f" {close_token}"
    if not remainder.endswith(suffix):
        return None
    return remainder[: -len(suffix)]


def parse_marker_line(fmt: RegionFormat, line: str) -> BeginMarker | EndMarker | None:
    """Parse one line as a ``marshal-seed:begin``/``marshal-seed:end``
    marker in ``fmt``'s comment style.

    Only GUARANTEES recognition of the EXACT canonical, single-space
    grammar ``render_begin``/``render_end`` produce -- this module owns
    line-level grammar only (its own module docstring's Never bullets). A
    line whose delimiter spacing, tag, or field syntax varies from that
    exact shape (irregular whitespace, a CRLF ending) is unspecified: it
    may return ``None`` (ordinary content) or raise ``MarkerError``
    (malformed), depending on exactly where the variance falls -- see the
    module docstring. Recovering a hand-edited or otherwise non-canonical
    marker predictably is a future story's job (S-8.2), which
    re-normalizes a file before consulting this grammar.

    Returns ``None`` for an ordinary, non-marker line (including a
    same-format comment that is not a marshal-seed marker at all) -- this
    is the normal, non-error case, needed by a future story's whole-file
    scan (S-8.2) to skip every line that is not a marker. Raises
    ``MarkerError`` for a line that matches the delimiter shape exactly and
    carries the ``marshal-seed:`` tag, but fails the grammar past that point
    (a malformed field, an unparseable ``model-version``, or a name/sha
    outside its own charset). Raises ``NotImplementedError`` for
    ``RegionFormat.SLASHSTAR`` (reserved, unimplemented in V1) --
    unconditionally, before looking at ``line`` at all, matching
    ``render_begin``/``render_end``.
    """
    fmt = _coerce_format(fmt)
    if fmt is RegionFormat.SLASHSTAR:
        raise NotImplementedError("RegionFormat.SLASHSTAR is reserved, unimplemented in V1")
    body = _strip_delimiters(fmt, line)
    if body is None or not body.startswith(f"{_MARKER_TAG}:"):
        return None

    begin_match = _BEGIN_BODY_PATTERN.fullmatch(body)
    if begin_match is not None:
        try:
            model_version = ModelVersion.parse(begin_match.group("model_version"))
        except InvalidVersionError as exc:
            raise MarkerError(f"malformed marshal-seed marker line {line!r}: {exc}") from exc
        return BeginMarker(
            region=begin_match.group("region"),
            model_version=model_version,
            sha=begin_match.group("sha"),
        )

    end_match = _END_BODY_PATTERN.fullmatch(body)
    if end_match is not None:
        return EndMarker(region=end_match.group("region"))

    raise MarkerError(f"malformed marshal-seed marker line: {line!r}")
