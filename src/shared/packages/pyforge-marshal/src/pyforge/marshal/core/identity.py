"""Story identity: the sole owner of the story-key format across every
external form (Story 1.2, architecture spine AD-23/AD-24/AD-38).

The loop, the journal, the spec archive, the merge subject, and the
dashboard must never key a story differently -- the documented incident
this guards against is the harness's own parser silently dropping
letter-suffixed keys (``2-6a``) and halving the actionable feed.
``normalize()`` is the one parser; one render function exists per external
form (feed key, filename slug, branch segment, merge subject); a meta-test
(``tests/meta/test_ad23_inline_key_format_guard.py``) asserts no other
module string-formats a story key inline.

``StoryKey``'s canonical key is ``<epic>.<seq>`` with an optional ordered
suffix, preserved and lowercased on read (AD-38) -- **not** "purely numeric
on both parts" as AD-23's own rule text still literally says: that sentence
predates AD-38 (added the same day) and is superseded here, per epics.md's
own already-correct Story 1.2 AC ("preserved and normalized") and the
harness's live ``--story`` flag, which documents accepting a split suffix
(``2-6a``). Rejecting a suffix would make ``normalize()`` reject input the
very harness Marshal wraps accepts.

``render_merge_subject``/``parse_merge_subject`` are the one render/parse
pair for AD-24's merge-subject form: the template is a plain string owned
by the caller (a future policy layer, not this module) containing exactly
one ``{key}`` placeholder; parsing is exact positional slicing on the
template's fixed literal prefix/suffix around that placeholder, never a
second regex.

``resolve_feed()`` is AD-38's completeness guarantee: ``total`` is always
the RAW pre-parse count (``len(raw_keys)``), never the post-parse count --
the latter would let a silently-dropped suffix report a false "N of N",
reproducing the exact incident AD-38 exists to prevent.

This module is pure data: no I/O, no subprocess, no clock, no
``pyforge.marshal.adapters`` (AD-4) -- only ``re``, ``dataclasses``,
``collections.abc``, and ``.model`` for ``Finding``/``Severity``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from .model import Finding, Severity

# Either `.` or `-` separates epic/seq on input; the suffix, if present, is a
# single letter (case-normalized by the caller). The lookahead (rather than
# `.fullmatch()`) requires the token to end at the input's end or at the next
# `.`/`-` separator -- so trailing descriptive text (a filename slug's title,
# a merge subject's surrounding words) is accepted and discarded, while text
# glued directly onto the key with no separator (`"1-23extra"`) is rejected
# rather than silently truncated. Matched with `.match()` (anchors at
# position 0), never `.search()` -- a key must LEAD the input, not appear
# anywhere inside it.
_KEY_RE = re.compile(
    r"(?P<epic>[0-9]+)[.\-](?P<seq>[0-9]+)(?P<suffix>[A-Za-z])?(?=$|[.\-])"
)

# The one placeholder `render_merge_subject`/`parse_merge_subject` own (AD-24).
# Any other placeholder in a caller's template (a run id, a target branch) is
# the caller's job to resolve before calling either function.
_KEY_PLACEHOLDER = "{key}"


class MalformedStoryKeyError(ValueError):
    """Raised by ``normalize()`` when ``raw`` does not contain a leading
    ``<epic>[.-]<seq><suffix>?`` token -- registers as ``MRS-IDENT-001``.
    Never silently coerced or truncated."""


class MergeSubjectConformanceError(ValueError):
    """Raised by ``parse_merge_subject()`` when ``subject`` does not conform
    to ``template``'s fixed literal shape around the one ``{key}``
    placeholder -- registers as ``MRS-IDENT-002``. Wraps every failure mode
    (a non-``str`` subject, mismatched prefix/suffix, or a malformed
    extracted key) so a caller only ever needs to catch this one exception
    type. Carries a ``.finding`` attribute: the real ``MRS-IDENT-002``
    ``Finding``, ready to feed into ``verdict.compute_verdict`` the same way
    ``resolve_feed``'s ``.findings`` tuple is used."""

    finding: Finding


@dataclass(frozen=True, order=True)
class StoryKey:
    """The canonical story key: ``<epic>.<seq>`` with an optional ordered
    single-letter suffix (AD-23, AD-38). ``suffix`` defaults to ``""``, never
    ``None`` -- ``order=True``'s field-tuple comparison then gives correct
    total ordering for free, since ``"" < "a" < "b"`` lexicographically:
    ``StoryKey(6, 1) < StoryKey(6, 1, "a") < StoryKey(6, 1, "b")``.

    ``__post_init__`` validates the invariants ``normalize()`` always
    produces (non-negative ``epic``/``seq``, ``suffix`` either ``""`` or a
    single lowercase ``a``-``z`` letter) -- matching ``model.py``'s
    ``Finding``/``Envelope`` convention of enforcing invariants at
    construction, not just via the one blessed constructor path. Without
    this, direct construction (bypassing ``normalize()``) could silently
    produce e.g. ``StoryKey(-1, 999, "ZZ")``.
    """

    epic: int
    seq: int
    suffix: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.epic, int) or isinstance(self.epic, bool) or self.epic < 0:
            raise ValueError(f"epic must be a non-negative int, got {self.epic!r}")
        if not isinstance(self.seq, int) or isinstance(self.seq, bool) or self.seq < 0:
            raise ValueError(f"seq must be a non-negative int, got {self.seq!r}")
        # An explicit ASCII range, not `islower() and isalpha()` -- those are
        # Unicode-wide, so they'd accept e.g. "ß" while the error message
        # below promises a-z, minting a key normalize() can never round-trip.
        if not isinstance(self.suffix, str) or (
            self.suffix and (len(self.suffix) != 1 or not ("a" <= self.suffix <= "z"))
        ):
            raise ValueError(
                f"suffix must be '' or a single lowercase a-z letter, got {self.suffix!r}"
            )

    def __str__(self) -> str:
        """The canonical dot form, e.g. ``"1.2"`` or ``"6.1a"``."""
        return f"{self.epic}.{self.seq}{self.suffix}"


def normalize(raw: str) -> StoryKey:
    """The sole parser (AD-23): strips surrounding whitespace, matches a
    leading ``<epic>[.-]<seq><suffix>?`` token (either separator accepted on
    input), and discards any trailing text after it -- so a bare feed key
    (``"1.2"``), a filename-slug/branch-segment token
    (``"1-2-story-title"``), or a merge-subject's already-extracted key
    substring all normalize uniformly. A present suffix is lowercased, never
    dropped. Raises ``MalformedStoryKeyError`` naming ``raw`` if no leading
    token matches -- including when ``raw`` isn't even a ``str`` (a real
    footgun: YAML parses an unquoted ``1.2:`` feed key as the float ``1.2``,
    not the string ``"1.2"``; without this guard that crashed with a raw
    ``AttributeError`` instead of the documented, reported failure)."""
    if not isinstance(raw, str):
        raise MalformedStoryKeyError(
            f"malformed story key: expected a str, got {raw!r} ({type(raw).__name__})"
        )
    match = _KEY_RE.match(raw.strip())
    if match is None:
        raise MalformedStoryKeyError(
            f"malformed story key: {raw!r} -- expected a leading "
            "<epic>[.-]<seq><suffix>? token"
        )
    suffix = match.group("suffix") or ""
    return StoryKey(
        epic=int(match.group("epic")),
        seq=int(match.group("seq")),
        suffix=suffix.lower(),
    )


def _require_story_key(key: StoryKey) -> None:
    """Every render function's type guard. Without it, ``render_feed_key``'s
    bare ``str(key)`` would silently echo un-normalized input (e.g. the raw
    string ``"6-1A"``) as if it were a canonical feed key -- the exact
    silent coercion this module exists to prevent -- and the hyphen-form
    renderers would fail with an incidental ``AttributeError`` instead of a
    typed rejection."""
    if not isinstance(key, StoryKey):
        raise TypeError(f"key must be a StoryKey, got {key!r}")


def render_feed_key(key: StoryKey) -> str:
    """The feed-key external form: the dot form, e.g. ``"6.1a"``. Rejects a
    non-``StoryKey`` ``key`` -- only canonical keys reach external forms."""
    _require_story_key(key)
    return str(key)


def _hyphen_form(key: StoryKey) -> str:
    _require_story_key(key)
    return f"{key.epic}-{key.seq}{key.suffix}"


def render_filename_slug(key: StoryKey) -> str:
    """The filename-slug external form: the hyphen form, e.g. ``"6-1a"``.
    Takes no descriptive title text -- that's the caller's concern, not
    identity's."""
    return _hyphen_form(key)


def render_branch_segment(key: StoryKey) -> str:
    """The branch-segment external form: the hyphen form, e.g. ``"6-1a"``.
    A distinct function from ``render_filename_slug`` per AD-23, even though
    today's output coincides -- so the two consumers can't silently diverge
    later without a code change in exactly one place."""
    return _hyphen_form(key)


def _split_template(template: str) -> tuple[str, str]:
    """Split ``template`` on its one ``{key}`` placeholder into the fixed
    literal ``(prefix, suffix)`` around it. Raises ``ValueError`` if
    ``template`` isn't a ``str`` or does not contain exactly one
    occurrence."""
    if not isinstance(template, str):
        raise ValueError(f"template must be a str, got {template!r}")
    if template.count(_KEY_PLACEHOLDER) != 1:
        raise ValueError(
            f"template must contain exactly one {_KEY_PLACEHOLDER!r} "
            f"placeholder, got {template!r}"
        )
    prefix, suffix = template.split(_KEY_PLACEHOLDER, 1)
    return prefix, suffix


def render_merge_subject(key: StoryKey, template: str) -> str:
    """The merge-subject external form (AD-24): substitutes ``key``'s hyphen
    form into ``template``'s one ``{key}`` placeholder. Raises ``ValueError``
    if ``template`` doesn't contain exactly one such placeholder."""
    prefix, suffix = _split_template(template)
    return f"{prefix}{render_filename_slug(key)}{suffix}"


def parse_merge_subject(subject: str, template: str) -> StoryKey:
    """The inverse of ``render_merge_subject`` (AD-24): slices ``subject``
    against ``template``'s fixed literal prefix/suffix around its one
    ``{key}`` placeholder (exact positional slicing, never a second regex)
    and re-normalizes the extracted middle. Any failure -- a non-``str``
    ``subject``, a malformed template, a mismatched prefix/suffix, an
    extracted span shorter than the template's fixed literal text, or a
    middle that doesn't parse -- is wrapped into
    ``MergeSubjectConformanceError`` (chained ``from exc``) so a caller only
    ever needs to catch this one exception type. The raised exception's
    ``.finding`` attribute is a real ``MRS-IDENT-002`` ``Finding`` -- the
    registry's second registered code, constructed here so it has an actual
    caller rather than being registered/classified with nothing behind it."""
    try:
        if not isinstance(subject, str):
            raise ValueError(f"subject must be a str, got {subject!r}")
        prefix, suffix = _split_template(template)
        if not subject.startswith(prefix) or not subject.endswith(suffix):
            raise ValueError(
                f"subject {subject!r} does not start with {prefix!r} and "
                f"end with {suffix!r}"
            )
        middle_start = len(prefix)
        middle_end = len(subject) - len(suffix)
        if middle_end < middle_start:
            raise ValueError(
                f"subject {subject!r} is shorter than template {template!r}'s "
                "fixed literal text"
            )
        return normalize(subject[middle_start:middle_end])
    except ValueError as exc:
        message = (
            f"subject {subject!r} does not conform to template {template!r}: "
            f"{exc}"
        )
        error = MergeSubjectConformanceError(message)
        error.finding = Finding(
            code="MRS-IDENT-002",
            severity=Severity.ERROR,
            message=message,
            path=subject if isinstance(subject, str) else repr(subject),
        )
        raise error from exc


@dataclass(frozen=True)
class FeedResolution:
    """The result of resolving a raw story-reference feed (AD-38):
    ``resolved`` (normalized keys, input order), ``unresolved`` (the raw
    strings that failed to parse), ``total`` (the RAW pre-parse count --
    F-13's fix, never the post-parse count), and ``findings`` (one
    ``MRS-IDENT-001`` ``Finding`` per unresolved raw key, ready to feed into
    ``verdict.compute_verdict``).

    ``__post_init__`` enforces the completeness arithmetic at construction
    (matching ``model.py``'s ``Finding``/``Envelope`` and ``StoryKey``'s own
    convention): ``total == len(resolved) + len(unresolved)`` and one
    finding per unresolved entry. Without this, direct construction
    (bypassing ``resolve_feed()``) could fabricate the false "N of M"
    attestation AD-38 exists to prevent."""

    resolved: tuple[StoryKey, ...]
    unresolved: tuple[str, ...]
    total: int
    findings: tuple[Finding, ...]

    def __post_init__(self) -> None:
        if self.total != len(self.resolved) + len(self.unresolved):
            raise ValueError(
                f"total ({self.total}) must equal len(resolved) + "
                f"len(unresolved) ({len(self.resolved)} + "
                f"{len(self.unresolved)}) -- every raw entry either resolves "
                "or is reported (AD-38)"
            )
        if len(self.findings) != len(self.unresolved):
            raise ValueError(
                f"findings ({len(self.findings)}) must carry exactly one "
                f"entry per unresolved key ({len(self.unresolved)})"
            )


def resolve_feed(raw_keys: Sequence[str]) -> FeedResolution:
    """Resolve every entry in ``raw_keys`` via ``normalize()``. ``total`` is
    ``len(raw_keys)`` -- the raw pre-parse count -- so a silently-dropped
    suffix can never report a false "N of N" (F-13, AD-38). Malformed
    entries are reported, never raised: each contributes its raw string to
    ``unresolved`` and a ``MRS-IDENT-001`` error-severity ``Finding`` naming
    it to ``findings``. An empty feed resolves to a clean 0-of-0 -- whether
    an empty feed is itself an error is the caller's policy, not identity's.
    A bare ``str`` feed is rejected loudly: a ``str`` satisfies
    ``Sequence[str]``, so ``resolve_feed("1.2")`` would otherwise shred into
    per-character garbage findings (the same footgun ``model.py``'s
    ``Envelope`` guards ``assumptions`` against)."""
    if isinstance(raw_keys, str):
        raise TypeError(
            "raw_keys must be a sequence of story references, not a bare "
            f"str: {raw_keys!r}"
        )
    total = len(raw_keys)
    resolved: list[StoryKey] = []
    unresolved: list[str] = []
    findings: list[Finding] = []
    for raw in raw_keys:
        try:
            resolved.append(normalize(raw))
        except MalformedStoryKeyError:
            # `raw` may not even be a str (e.g. a YAML-parsed float feed
            # key) -- `unresolved`/`Finding.path` are both str-typed, so a
            # non-str raw entry is repr'd for reporting rather than passed
            # through, which would otherwise crash `Finding.__post_init__`'s
            # own `path must be a str or None` check. But repr() of e.g. the
            # float 1.2 is the quoteless, perfectly-valid-looking "1.2" --
            # so the message also names the type, or the diagnostic would
            # claim a well-formed key failed to resolve.
            if isinstance(raw, str):
                display = raw
                message = f"unresolved story reference: {raw}"
            else:
                display = repr(raw)
                message = (
                    f"unresolved story reference: {display} "
                    f"({type(raw).__name__})"
                )
            unresolved.append(display)
            findings.append(
                Finding(
                    code="MRS-IDENT-001",
                    severity=Severity.ERROR,
                    message=message,
                    path=display,
                )
            )
    return FeedResolution(
        resolved=tuple(resolved),
        unresolved=tuple(unresolved),
        total=total,
        findings=tuple(findings),
    )
