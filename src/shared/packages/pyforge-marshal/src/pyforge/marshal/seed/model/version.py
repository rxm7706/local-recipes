"""Self-contained SemVer 2.0.0 parser/comparator for the seed model's
``model_version`` clock (Story 7.4, architecture A-05/AD-55).

A-05 names two independent clocks: ``seed_model_version`` (this package's
own release) and ``model_version`` (the operating model a manifest entry's
``since``/``until`` bounds are keyed against). This module owns the second
clock's arithmetic only -- comparing two version strings correctly,
including SemVer 2.0.0's pre-release precedence rules, which Python cannot
give for free (``int`` and ``str`` are not orderable against each other, so
a naive ``tuple(prerelease) < tuple(other_prerelease)`` raises ``TypeError``
the moment one side mixes a numeric identifier like ``"1"`` with an
alphanumeric one like ``"alpha"``).

No dependency is added for this (`architecture Stack table`, this story's
own Never bullet): the ``packaging`` library models PEP 440, a different
(and incompatible) precedence scheme, and pulling in a real SemVer package
for ~80 lines of grammar is exactly the kind of speculative dependency
``Simplicity First`` forbids.

``ModelVersion.parse`` implements the grammar from
<https://semver.org> (BNF + regex, section 2/9/10) verbatim: a version core
of exactly three non-negative, non-leading-zero integers; an optional
dot-separated pre-release identifier list (each identifier is either a
non-leading-zero numeric string or an ASCII-alphanumeric-plus-hyphen
string); and optional dot-separated build metadata (never affects
precedence -- section 10 -- so it round-trips through ``parse`` but is
excluded from ``__eq__``/ordering).

Ordering is implemented via ``functools.total_ordering``: the dataclass's
own generated ``__eq__`` already does the right thing (tuple equality over
``major``/``minor``/``patch``/``prerelease``, with ``build`` excluded via
``field(compare=False)`` -- SemVer 2.0.0 section 10's "MUST be ignored"
rule for precedence, generalized to equality too since two builds of the
same release are the same version). Only ``__lt__`` needs hand-written
logic, because comparing pre-release identifiers requires knowing, per
identifier, whether both sides are numeric (compare as integers) or not
(compare as ASCII strings) -- section 11's rule that this is a MIXED
comparison, never a uniform tuple compare.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import total_ordering

from pyforge.core.errors import PyforgeError

# No ^/$ anchors -- matched with .fullmatch(), not .match(), so a trailing
# newline can never sneak a malformed version string past the check (see
# core/findings.py's CODE_PATTERN for the identical convention and the
# Python `re` pitfall it documents: `$` alone matches immediately before a
# trailing "\n").
_VERSION_CORE = r"(?:0|[1-9]\d*)"
_PRERELEASE_IDENTIFIER = r"(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
_BUILD_IDENTIFIER = r"[0-9a-zA-Z-]+"

_SEMVER_PATTERN = re.compile(
    rf"(?P<major>{_VERSION_CORE})\.(?P<minor>{_VERSION_CORE})\.(?P<patch>{_VERSION_CORE})"
    rf"(?:-(?P<prerelease>{_PRERELEASE_IDENTIFIER}(?:\.{_PRERELEASE_IDENTIFIER})*))?"
    rf"(?:\+(?P<build>{_BUILD_IDENTIFIER}(?:\.{_BUILD_IDENTIFIER})*))?",
    # SemVer 2.0.0's grammar is ASCII-only -- without this flag, `\d` also
    # matches non-ASCII Unicode decimal digits (e.g. Arabic-Indic), which
    # would let a non-conformant string like "1٠3.0.0" parse as a
    # silently-wrong `major=103` instead of raising InvalidVersionError.
    re.ASCII,
)

# Single-identifier forms, for validating a directly-constructed
# ModelVersion (parse() gets this for free from _SEMVER_PATTERN, but
# __post_init__ is a second, unguarded entry point -- see its docstring).
_PRERELEASE_IDENTIFIER_PATTERN = re.compile(_PRERELEASE_IDENTIFIER, re.ASCII)
_BUILD_IDENTIFIER_PATTERN = re.compile(_BUILD_IDENTIFIER, re.ASCII)


class InvalidVersionError(PyforgeError, ValueError):
    """Raised by ``ModelVersion.parse`` when a string does not conform to
    the SemVer 2.0.0 grammar (leading zeros, wrong component count, illegal
    characters, or an empty/non-string input).

    Story 14.3, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``ValueError`` stays in the MRO."""


def _is_numeric_identifier(identifier: str) -> bool:
    # `.isdigit()` alone is a trap: it is True for characters that are not
    # decimal at all (superscripts like "²", other Unicode digit forms), so
    # a bare `.isdigit()` guard classifies a non-decimal string as numeric.
    # Same reason `adapters/harness_bmadloop.py` rejects it.
    # `__post_init__` already confines identifiers to the ASCII grammar;
    # this is the belt to that braces.
    return identifier.isascii() and identifier.isdecimal()


def _compare_numeric_identifier(left: str, right: str) -> int:
    """Compare two decimal identifier strings numerically WITHOUT ``int()``.

    SemVer 2.0.0 puts no length bound on a numeric pre-release identifier,
    but CPython refuses ``int()`` past 4300 digits -- so converting here
    would raise a raw ``ValueError`` straight out of ``__lt__``, and (via
    ``in_range``) straight past ``load_manifest``'s ``ManifestError``-only
    contract. Comparing as digit strings is total for every length: with
    leading zeros removed, the longer string is always the larger number,
    and equal-length decimal strings compare numerically in lexicographic
    order. The ``lstrip`` also keeps the relation correct for a
    leading-zero identifier the grammar should have rejected, so this stays
    total even if a future entry point skips validation.
    """
    left_digits = left.lstrip("0") or "0"
    right_digits = right.lstrip("0") or "0"
    if len(left_digits) != len(right_digits):
        return -1 if len(left_digits) < len(right_digits) else 1
    return (left_digits > right_digits) - (left_digits < right_digits)


def _compare_prerelease_identifier(left: str, right: str) -> int:
    """Per-identifier SemVer 2.0.0 precedence (section 11.4): numeric
    identifiers compare numerically; alphanumeric identifiers compare in
    ASCII sort order; a numeric identifier ALWAYS has lower precedence than
    an alphanumeric one, regardless of value. Returns -1/0/1."""
    left_numeric = _is_numeric_identifier(left)
    right_numeric = _is_numeric_identifier(right)
    if left_numeric and right_numeric:
        return _compare_numeric_identifier(left, right)
    if left_numeric != right_numeric:
        return -1 if left_numeric else 1
    return (left > right) - (left < right)


@total_ordering
@dataclass(frozen=True)
class ModelVersion:
    """One parsed SemVer 2.0.0 version. ``build`` is excluded from equality
    and ordering (``compare=False``) -- section 10's "build metadata MUST
    be ignored when determining version precedence" rule."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = field(default=(), compare=False)

    def __post_init__(self) -> None:
        """Validate the SemVer 2.0.0 grammar on the FIELDS, not just on the
        parsed string. ``parse`` is not the only way in -- tests, a future
        state deserializer, and ``dataclasses.replace`` all construct this
        directly -- and an identifier that violates the grammar breaks
        ordering itself: ``("01",)`` vs ``("1",)`` compares equal
        numerically yet unequal by ``__eq__``, so the pair is neither <, >,
        nor ==, and ``sorted``/``bisect`` silently misbehave."""
        for name, value in (("major", self.major), ("minor", self.minor), ("patch", self.patch)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")
            try:
                text = str(value)
            except ValueError as exc:
                # `parse` already converts an over-long numeric component to
                # InvalidVersionError, but this second entry point accepted
                # any `int` -- and CPython refuses to RENDER one past 4300
                # digits, so `__str__` (and therefore every operator-facing
                # message that interpolates a version, including this
                # module's own `until (...) must be strictly greater than
                # since (...)`) blew up while formatting the error instead
                # of reporting it.
                raise ValueError(f"{name} has an unusable numeric component: {exc}") from exc
            if value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {text}")
        for name, value, pattern in (
            ("prerelease", self.prerelease, _PRERELEASE_IDENTIFIER_PATTERN),
            ("build", self.build, _BUILD_IDENTIFIER_PATTERN),
        ):
            if not isinstance(value, tuple) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"{name} must be a tuple of str, got {value!r}")
            for item in value:
                if pattern.fullmatch(item) is None:
                    raise ValueError(f"{name} identifier {item!r} is not a valid SemVer 2.0.0 identifier")

    @staticmethod
    def parse(text: str) -> ModelVersion:
        """Parse a SemVer 2.0.0 version string. Raises
        ``InvalidVersionError`` on anything that does not fully match the
        grammar -- a leading zero in any numeric component, a component
        count other than three, an illegal character, or a non-``str``
        input."""
        if not isinstance(text, str):
            raise InvalidVersionError(f"version must be a str, got {text!r}")
        match = _SEMVER_PATTERN.fullmatch(text)
        if match is None:
            raise InvalidVersionError(f"{text!r} is not a valid SemVer 2.0.0 version string")
        prerelease_text = match.group("prerelease")
        build_text = match.group("build")
        try:
            core = tuple(int(match.group(name)) for name in ("major", "minor", "patch"))
        except ValueError as exc:
            # A grammatically valid but absurd component (CPython refuses
            # int() past 4300 digits) would otherwise escape as a raw
            # ValueError, past every caller catching InvalidVersionError.
            raise InvalidVersionError(f"{text!r} has an unusable numeric component: {exc}") from exc
        return ModelVersion(
            major=core[0],
            minor=core[1],
            patch=core[2],
            prerelease=tuple(prerelease_text.split(".")) if prerelease_text else (),
            build=tuple(build_text.split(".")) if build_text else (),
        )

    def __str__(self) -> str:
        """Round-trip back to the SemVer string ``parse`` accepts. Without
        this, every operator-facing message that interpolates a version
        (this module's own ``until``/``since`` error, and any later story
        writing ``model_version`` to state) prints the dataclass repr."""
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += "-" + ".".join(self.prerelease)
        if self.build:
            text += "+" + ".".join(self.build)
        return text

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ModelVersion):
            return NotImplemented
        self_core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if self_core != other_core:
            return self_core < other_core
        # Version cores are equal -- section 11.3: a version WITH a
        # pre-release has LOWER precedence than the same core WITHOUT one.
        if not self.prerelease or not other.prerelease:
            return bool(self.prerelease) and not other.prerelease
        for left, right in zip(self.prerelease, other.prerelease):
            comparison = _compare_prerelease_identifier(left, right)
            if comparison != 0:
                return comparison < 0
        # Every shared identifier compared equal -- section 11.4's tail
        # rule: fewer pre-release fields has LOWER precedence.
        return len(self.prerelease) < len(other.prerelease)


def in_range(version: ModelVersion, since: ModelVersion | None, until: ModelVersion | None) -> bool:
    """Half-open range check: ``[since, until)``. ``since is None`` means no
    lower bound; ``until is None`` means no upper bound. An entry is
    retired starting exactly AT ``until`` (excluded), and included starting
    exactly AT ``since`` (included)."""
    if since is not None and version < since:
        return False
    return until is None or version < until
