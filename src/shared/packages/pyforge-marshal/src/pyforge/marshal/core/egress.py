"""AD-34's single redacting egress boundary (Story 2.6): a ``Redacted``
wrapper type, ``to_redacted()`` -- the ONE redacting serializer -- a pure
``build_gate_record`` shaping function, and ``EGRESS_PORTS``, the one
port-classification registry.

**Why a durable gate-evidence record.** ``marshal gate evaluate`` (Story
2.1) only prints its envelope to stdout -- nothing durably records what a
gate evaluation checked or said. ``build_gate_record`` shapes an
already-evaluated gate's facts (each verify command's already-classified
report, an already-selected scope-check verdict, an already-known tree
revision, an already-obtained UTC timestamp) into the one dict shape
``schemas/gate-record.json`` describes, mirroring ``core.gate.
classify_outcome``'s own "caller already gathered the fact" convention:
this module does no I/O, no VCS call, no clock read (AD-4) -- ``cli/gate.py``
wiring a real caller is explicitly deferred (see ``deferred-work.md``; the
epics.md Surface line for this story omits ``cli/gate.py``/``core/gate.py``,
mirroring Story 2.4's identical "shipped a fully-tested pure function with
zero CLI wiring" precedent).

**Why two redaction mechanisms coexist.** ``core.policy.redact()`` (Story
1.3) redacts by field NAME for policy-VALUE DISPLAY (``cli/config.py``) --
a narrower, already-shipped, differently-scoped mechanism this module does
not touch. ``to_redacted()`` is the NEW, broader AD-34 serializer for
durable RECORDS: it reuses ``policy.is_secret_key``/``REDACTED_SENTINEL``
(no second secret-key vocabulary) but ALSO scans every string value against
a small closed set of known token-shape regexes -- ``policy.redact()``
never had shape scanning, since a policy field's value is never a raw
external token.

**Why the registry lives here, not scattered per-port-file.**
``ports/__init__.py``'s Story-1.1 placeholder said "each port will declare
egress: true|false", but the AC requires ONE registry -- and a per-file
declaration importing ``Redacted`` from this module while this module also
imported that port module would risk an import cycle. Keying
``EGRESS_PORTS`` by class-name STRING (not an imported class reference)
avoids this module needing to import ``ports/*`` at all -- only
``tests/meta/test_ad34_egress_registry_completeness.py`` (test code,
outside the package's own layering rules) imports both sides.

**Never raises a new ``MRS-*`` finding code** for malformed
``build_gate_record`` input -- a caller bug (an unparseable timestamp, a
malformed story key, an out-of-vocabulary verdict) raises ``ValueError``/
``MalformedStoryKeyError`` directly, the same "raise for contract
violations" convention ``core.policy.EffectivePolicy``/``core.identity.
StoryKey`` already use for direct-construction misuse, and mirroring Story
2.5's ``describe_gate_mode`` precedent (an out-of-vocabulary ``gate_mode``
raises rather than reporting a ``Finding``).

This module is pure data: no I/O, no subprocess, no clock (AD-4) -- only
``json``, ``re``, ``collections.abc``, ``dataclasses``, ``datetime``, and
this package's own ``.identity``/``.model``/``.policy``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from . import identity
from .model import Verdict
from .policy import REDACTED_SENTINEL, is_secret_key

# The closed set of known token SHAPES (Boundaries & Constraints): a GitHub
# PAT, a GitHub fine-grained PAT, an AWS access key, and a generic `sk-`
# secret-key prefix (the shape several LLM/API providers use). Scanned
# against EVERY str value (keyed or not) -- independent of, and in addition
# to, the field-NAME-based `is_secret_key` check below. Private: no module
# other than this one may reference it (structurally enforced by
# tests/meta/test_ad34_egress_registry_completeness.py) -- the whole point
# of a single redacting serializer is that no call site can hand-roll its
# own redaction against a copy of this vocabulary.
#
# Two boundary fixes over a naive "prefix + exact length" pattern (review
# findings, both verified live):
# (1) A leading `(?<![A-Za-z0-9_])` negative lookbehind before every
#     prefix -- without it, `sk-` (and `ghp_`/`AKIA`) match mid-word, so an
#     ordinary value like a `tree_revision`/branch named
#     `"risk-8f3a9b2c1d4e5f6a7b8c9d0e1f2a3b4c"` had its trailing hex mangled
#     as if `"sk-8f3a...` were a leaked secret -- corrupting an otherwise
#     ordinary, non-secret record field.
# (2) `{36,}`/`{16,}` (open-ended), not `{36}`/`{16}` -- a fixed-length
#     quantifier only consumes exactly that many characters, so a REAL
#     token longer than the hardcoded length (e.g. `"ghp_" + "a" * 40`)
#     redacted its first 36 characters and left the trailing 4 in
#     plaintext: `"***REDACTED***aaaa"`, silently leaking a fragment of the
#     very secret this fixture exists to catch. An open-ended quantifier
#     consumes the WHOLE contiguous alnum run instead, so nothing partial
#     survives.
# (3) A SEPARATOR-TOLERANT `sk-` variant (follow-up review finding, verified
#     live). `sk-[A-Za-z0-9]{20,}` requires 20 CONTIGUOUS alnum characters
#     after `sk-`, which neither dominant real-world format satisfies: an
#     OpenAI project key (`sk-proj-<48>T3BlbkFJ<48>`) and an Anthropic key
#     (`sk-ant-api03-<40>-<40>`) both put a `-` within the first 8
#     characters, so BOTH passed through in FULL PLAINTEXT -- the exact
#     credential shape a Marshal gate record is most likely to capture,
#     since Marshal's own agent sessions authenticate with one. The same
#     gap leaked the TAIL of any separated token (`"sk-" + "c"*25 + "-" +
#     "d"*25` redacted only the first run: `"***REDACTED***-ddd..."`).
#     `sk-[A-Za-z0-9_-]{40,}` covers both, with the length floor raised to
#     40 deliberately: every real provider key is far longer than 40
#     characters, while an ordinary hyphenated value that merely STARTS
#     with `sk-` (a `pytest -k sk-some-selector` expression, a branch name)
#     is almost never 40+ characters of unbroken `[A-Za-z0-9_-]`. The
#     residual over-redaction risk is accepted: mangling a rare command
#     string in an evidence record is strictly less harmful than writing a
#     live API key to durable storage.
#
# (4) A TRAILING `_TOKEN_RUN_TAIL` on every pattern (second follow-up review
#     finding, verified live). Fixes (2) and (3) each closed the tail leak
#     for one shape and left it open for another, because a pattern that
#     stops mid-run still substitutes a sentinel and leaves the remainder
#     in plaintext -- the same "the record LOOKS redacted while half the
#     secret sits beside it" failure, three passes running:
#       * `"sk-" + "c"*25 + "-" + "d"*12` -> `"***REDACTED***-dddddddddddd"`.
#         The separated run is 38 characters, UNDER the tolerant pattern's
#         40-char floor, so the contiguous `sk-[A-Za-z0-9]{20,}` matched the
#         leading run alone. Fix (3)'s own regression test happened to pick a
#         51-character run, clearing the floor and never exercising the gap.
#       * `"ghp_" + "a"*36 + "sk-" + "b"*45` -> `"***REDACTED***-bbbb..."`.
#         `ghp_[A-Za-z0-9]{36,}` greedily ate the `a`s AND the following
#         `sk`, destroying the `sk-` prefix the next pattern needed.
#     A trailing `[A-Za-z0-9_-]*` makes every match consume the WHOLE
#     adjoining token-ish run, so no partial tail can survive whichever
#     pattern happens to fire. It can only ever extend a substitution that
#     was already going to happen, so it adds no new over-redaction risk to
#     a value not already classified as a token.
#
# ORDER: the separator-tolerant `sk-` pattern is kept before the contiguous
# one for readability (most-specific first). Since fix (4), order is no
# longer load-bearing -- either `sk-` pattern now consumes the entire run --
# but the tolerant one is still required on its own: a real Anthropic key
# (`sk-ant-api03-...`) has only 3 contiguous alnum characters after `sk-`,
# so the contiguous pattern never matches it at all.
# (5) The GitHub prefix is `gh[pousr]_`, not `ghp_` alone, and the AWS one is
#     `AKIA|ASIA` (follow-up review finding, both verified live: each omitted
#     shape passed through in FULL PLAINTEXT while its covered sibling
#     redacted). `ghp_` is only the CLASSIC USER PAT. The same 36-character
#     body ships under `ghs_` (a GitHub App / Actions installation token --
#     what `GITHUB_TOKEN` and `gh` itself carry), `gho_` (an OAuth user
#     token, what a logged-in `gh` stores), `ghu_` (a user-to-server token)
#     and `ghr_` (a refresh token). `ghs_` is the single likeliest credential
#     to land in a gate record: it is what `git` echoes back inside the
#     remote URL of a failed push (`https://x-access-token:ghs_...@github.
#     com/o/r.git`), captured straight into a verify command's `stderr`.
#     `ASIA` is the AWS STS TEMPORARY access key ID -- byte-identical in
#     shape to `AKIA`, and the form anything assuming a role actually uses.
#     This stays within the Boundaries clause's "small closed set of known
#     token-shape regexes": these are the same four vocabularies spelled
#     completely, not new shape classes.
#
# (6) The lookbehind is `(?<![A-Za-z0-9])`, NOT `(?<![A-Za-z0-9_])` (follow-up
#     review finding, verified live: `"GITHUB_TOKEN_ghp_" + "a"*36` passed
#     through in full plaintext, because `_` is the most common
#     token-ADJACENT separator in env-var-shaped text and the lookbehind
#     blocked exactly that). A previous pass rejected this as "the same
#     knob pulled in opposite directions -- either fix re-opens the other";
#     that reasoning does not hold for the `_` half specifically, verified
#     against every over-redaction control in the suite: `risk-8f3a...`
#     (the case the lookbehind was added for) has an ALNUM `i` before `sk-`,
#     so dropping `_` from the class leaves it blocked exactly as before.
_TOKEN_RUN_TAIL = r"[A-Za-z0-9_-]*"
_TOKEN_LEAD = r"(?<![A-Za-z0-9])"
_TOKEN_SHAPE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(_TOKEN_LEAD + r"gh[pousr]_[A-Za-z0-9]{36,}" + _TOKEN_RUN_TAIL),
    re.compile(_TOKEN_LEAD + r"github_pat_[A-Za-z0-9_]{20,}" + _TOKEN_RUN_TAIL),
    re.compile(_TOKEN_LEAD + r"(?:AKIA|ASIA)[0-9A-Z]{16,}" + _TOKEN_RUN_TAIL),
    re.compile(_TOKEN_LEAD + r"sk-[A-Za-z0-9_-]{40,}" + _TOKEN_RUN_TAIL),
    re.compile(_TOKEN_LEAD + r"sk-[A-Za-z0-9]{20,}" + _TOKEN_RUN_TAIL),
)

# The one registry (AD-34), keyed by Protocol class NAME (a string, not an
# imported class) -- see the module docstring for why. `RecordPort` is the
# first and only port classified `egress: true`; the other four are already
# documented (or self-evidently, for VcsPort/HarnessPort) as non-egress --
# every path they touch stays inside the local filesystem/git repo/host.
EGRESS_PORTS: Mapping[str, bool] = {
    "ProcessPort": False,
    "FsPort": False,
    "HarnessPort": False,
    "VcsPort": False,
    "RecordPort": True,
}


@dataclass(frozen=True)
class Redacted:
    """An already-redacted, already-serialized payload (AD-34) -- the ONLY
    value type an egress-classified port (``RecordPort``) may accept, never
    a bare ``str``. The sole legitimate constructor is ``to_redacted()``;
    ``Redacted`` itself performs no redaction -- it is a type boundary, not
    a mechanism, so nothing stops a caller from wrapping already-secret text
    directly. What DOES stop that is structural: every real write path goes
    through ``to_redacted()`` by convention, and no call site can substitute
    its own token-shape vocabulary since ``_TOKEN_SHAPE_PATTERNS`` stays
    private to this module (guarded by a meta-test)."""

    text: str

    def __post_init__(self) -> None:
        # TypeError, not ValueError (review finding): the other two type
        # guards in this same three-call pipeline -- `to_redacted`'s
        # non-Mapping payload and `LocalFs.write_redacted_atomic`'s
        # non-`Redacted`/non-`Path` arguments -- both raise TypeError for
        # the identical "wrong type supplied" category, so a caller
        # wrapping the pipeline in one `except TypeError` handled two of
        # three failure points.
        # The TYPE only, never the value (follow-up review finding): an
        # unredacted payload interpolated into an exception message escapes
        # as a raw traceback on stderr. See `_safe_repr`. A whole rejected
        # payload is maximally secret-bearing AND may carry a secret that
        # matches no known shape, so shape-scanning it is not enough here --
        # naming the type is fully diagnostic and cannot leak.
        if not isinstance(self.text, str):
            raise TypeError(f"text must be a str, got {type(self.text).__name__}")


def _redact_string(value: str) -> str:
    """The shape half of redaction: replace every ``_TOKEN_SHAPE_PATTERNS``
    match with ``REDACTED_SENTINEL``, independent of whatever key (if any)
    ``value`` is stored under."""
    redacted = value
    for pattern in _TOKEN_SHAPE_PATTERNS:
        redacted = pattern.sub(REDACTED_SENTINEL, redacted)
    return redacted


def _safe_repr(value: object) -> str:
    """``repr(value)``, shape-scanned (follow-up review finding, verified
    live). Every diagnostic in this module interpolates caller-supplied data,
    and ``cli/main.py`` catches only ``SystemExit``/``KeyboardInterrupt``, so
    a contract violation lands as a raw traceback on stderr -- which the
    harness captures and logs. Without this, the ONE module whose stated
    purpose is keeping credentials out of a sink printed them itself:
    ``to_redacted("token=sk-ant-api03-...")`` raised ``TypeError: payload
    must be a Mapping, got 'token=sk-ant-api03-...'``, and
    ``_validate_command_report``'s ``{entry!r}`` echoed a whole command
    report including its captured ``stdout``. Diagnostics get the same
    redaction the record does -- nothing routes around ``_redact_string``."""
    return _redact_string(repr(value))


def _redact(value: object) -> object:
    """Recursively walk a dict/list/scalar payload. A ``Mapping``'s
    secret-shaped keys (``policy.is_secret_key``) have their value replaced
    outright -- the field-NAME half of redaction, reusing Story 1.3's
    existing suffix vocabulary rather than inventing a second one; every
    other value recurses (a nested ``Mapping``/``list``/``tuple``) or, for a
    bare ``str``, is shape-scanned via ``_redact_string``. Every other
    scalar (int, float, bool, ``None``) passes through unchanged.

    A ``str`` KEY is itself shape-scanned too (follow-up review finding,
    verified live: previously only VALUES were scanned, so a token-shaped
    key -- the natural shape of a captured environment, header map, or
    URL-keyed map, all of which a future egress caller may fold into a
    record -- was written verbatim). A key matching ``is_secret_key`` keeps
    its NAME (the name is not the secret; only its value is replaced), so
    only a key that literally CONTAINS a token shape is rewritten. Bound: two
    distinct token-shaped keys in one mapping collapse to a single sentinel
    key and the later value wins -- accepted, since the alternative is
    emitting the credential."""
    if isinstance(value, Mapping):
        redacted_map: dict[object, object] = {}
        for key, inner in value.items():
            if isinstance(key, str) and is_secret_key(key):
                # Shape-scan the NAME too (review finding, verified live):
                # the two halves are not mutually exclusive, and the
                # secret-key branch used to `continue` before the key ever
                # reached `_redact_string`, so a key that was BOTH
                # secret-shaped and token-shaped (`"ghp_" + "a"*36 +
                # "_TOKEN"`) had its value redacted while the credential in
                # its own name was emitted verbatim as a JSON key -- the one
                # case this function's own docstring claims is rewritten.
                redacted_map[_redact_string(key)] = REDACTED_SENTINEL
                continue
            redacted_map[_redact_string(key) if isinstance(key, str) else key] = _redact(inner)
        return redacted_map
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def to_redacted(payload: Mapping[str, object]) -> Redacted:
    """The ONE redacting serializer (AD-34): recursively redact ``payload``
    (see ``_redact``'s two-halved rule -- secret-shaped key names AND
    known token shapes anywhere), then ``json.dumps(..., sort_keys=True)``
    the result, wrapped in ``Redacted``. Raises ``TypeError`` if ``payload``
    is not a ``Mapping`` -- a contract violation, matching ``core.policy.
    compose()``'s own "not a bare str/Mapping" convention for its own
    ``project``/``flags`` parameters. A payload containing a non-JSON-safe
    value (a ``set``, ``bytes``, ``datetime``, ...) also raises ``TypeError``,
    naming the offending value -- review finding, verified live: without
    this, ``json.dumps`` raised its own unannotated ``TypeError`` deep
    inside this function instead of a documented failure mode, mirroring
    ``core.model.Envelope.__post_init__``'s own "wrap json.dumps's failure"
    precedent."""
    if not isinstance(payload, Mapping):
        # The TYPE only, never the value -- see `Redacted.__post_init__`.
        raise TypeError(f"payload must be a Mapping, got {type(payload).__name__}")
    redacted = _redact(payload)
    try:
        # allow_nan=False (follow-up review finding, verified live): the
        # default True emits bare `NaN`/`Infinity` tokens, which are NOT
        # valid RFC-8259 JSON -- so a payload carrying a float NaN wrote a
        # durable record no strict parser (jq, Go, Rust, a `parse_constant`
        # -guarded json.loads) can read back, silently, instead of the
        # TypeError this function's own docstring promises. With it False,
        # json.dumps raises ValueError, which is re-raised as the documented
        # TypeError alongside the unserializable-type case.
        text = json.dumps(redacted, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"payload contains a non-JSON-serializable value: {exc}") from exc
    return Redacted(text=text)


_REQUIRED_COMMAND_KEYS: frozenset[str] = frozenset({"command", "returncode", "resolvable"})
# `stdout`/`stderr` are the only OPTIONAL keys `schemas/gate-record.json`'s
# `commandReport` names -- matching `core.gate.classify_outcome`'s own report
# shape, which carries them only when `resolvable` is `True`. Together with
# `_REQUIRED_COMMAND_KEYS` this is the CLOSED key set: an entry naming any
# other key is rejected outright (review finding, verified live -- without
# this, an unrecognized key silently passed `build_gate_record` and only
# failed much later, and only in a test, against the schema's own
# `additionalProperties: false`, never at the point that actually produced
# the bad record).
_OPTIONAL_COMMAND_KEYS: frozenset[str] = frozenset({"stdout", "stderr"})
_ALL_COMMAND_KEYS: frozenset[str] = _REQUIRED_COMMAND_KEYS | _OPTIONAL_COMMAND_KEYS

# Kept CHARACTER-FOR-CHARACTER identical to `schemas/gate-record.json`'s own
# `timestamp` pattern (review finding, verified live). `datetime.
# fromisoformat` is far more permissive than that pattern on Python 3.11+:
# it also accepts a missing seconds field (`2026-08-03T00:00+00:00`), the
# compact offset forms `+0000`/`+00`, and the basic ISO form
# (`20260803T000000Z`). All four are legitimate UTC ISO-8601 and all four
# were ACCEPTED by `build_gate_record` and then REJECTED by the packaged
# schema -- so a well-behaved caller wrote a durable, `$id`-bearing record
# no consumer validating against the shipped contract would accept, while
# that schema's own description claimed "the pattern enforces what
# build_gate_record() itself enforces". `tests/unit/test_egress.py` pins the
# two spellings together in BOTH directions.
#
# Every date/time COMPONENT carries its real range (follow-up review finding,
# verified live). With bare `[0-9]{2}` groups the pattern -- and therefore the
# schema, which is pinned character-for-character to it -- green-lit
# `2026-13-45T99:99:99Z`, and worse, `2026-08-03T24:00:00Z` passed BOTH the
# schema and this producer while `datetime.fromisoformat` silently resolves
# hour 24 to `2026-08-04T00:00:00+00:00`: a durable evidence record whose
# stored text says one day and whose meaning is the next. Bound: a regex
# cannot express calendar validity, so `2026-02-30T12:00:00Z` still matches
# this pattern -- the producer rejects it via `fromisoformat`, the schema
# alone cannot. That asymmetry is now stated in the schema's own description
# rather than claimed away.
_TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
    r"[T ]([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]+)?(Z|[+-]00:00)$"
)


def _validate_command_report(entry: Mapping[str, object], index: int) -> dict[str, object]:
    """One ``commands`` entry must carry ``command``/``returncode``/
    ``resolvable`` -- mirrors ``core.gate.classify_outcome``'s own report
    shape -- and may additionally carry ``stdout``/``stderr`` (both, if
    present, validated as ``str``, matching the schema's own typing).  No
    other key is permitted. Returns a fresh plain ``dict`` (never an alias
    of ``entry``) -- safe to `dict()`-copy rather than deep-copy since every
    permitted key's value is now a validated immutable scalar (``str``,
    ``int``, ``bool``, or ``None``)."""
    # No message below echoes the whole `entry` (follow-up review finding,
    # verified live: `{entry!r}` printed a command report's captured `stdout`
    # verbatim, so a malformed report leaked exactly what this module exists
    # to redact). The index plus the offending key names identify the entry
    # precisely; individual values go through `_safe_repr`.
    if isinstance(entry, str) or not isinstance(entry, Mapping):
        raise ValueError(f"commands[{index}] must be a Mapping, got {type(entry).__name__}")
    missing = _REQUIRED_COMMAND_KEYS - set(entry.keys())
    if missing:
        raise ValueError(f"commands[{index}] is missing required key(s) {sorted(missing)}")
    unknown = set(entry.keys()) - _ALL_COMMAND_KEYS
    if unknown:
        # `sorted(map(repr, ...))`, not `sorted(...)` (review finding,
        # verified live): a Mapping is not required to have str keys, and
        # `sorted({1, "bogus"})` raises its own bare TypeError ("'<' not
        # supported between instances of 'int' and 'str'") from inside this
        # validator -- masking the ValueError this function documents for
        # every malformed-input case.
        raise ValueError(
            f"commands[{index}] has unknown key(s) {sorted(map(_safe_repr, unknown))} -- only "
            f"{sorted(_ALL_COMMAND_KEYS)} are permitted"
        )
    command = entry["command"]
    # `.strip()`, not `== ""` (follow-up review finding, verified live): a
    # whitespace-only command was accepted, storing an entry that proves
    # nothing in a record whose entire purpose is proving what was checked.
    if not isinstance(command, str) or not command.strip():
        raise ValueError(
            f"commands[{index}]['command'] must be a non-blank str, got {_safe_repr(command)}"
        )
    resolvable = entry["resolvable"]
    if not isinstance(resolvable, bool):
        raise ValueError(
            f"commands[{index}]['resolvable'] must be a bool, got {_safe_repr(resolvable)}"
        )
    returncode = entry["returncode"]
    if returncode is not None and (isinstance(returncode, bool) or not isinstance(returncode, int)):
        raise ValueError(
            f"commands[{index}]['returncode'] must be an int or None, "
            f"got {_safe_repr(returncode)}"
        )
    for key in _OPTIONAL_COMMAND_KEYS:
        if key in entry and not isinstance(entry[key], str):
            raise ValueError(
                f"commands[{index}][{key!r}] must be a str when present, got "
                f"{type(entry[key]).__name__}"
            )
    # Cross-field consistency (follow-up review finding, verified live). The
    # schema DOCUMENTS both invariants in prose -- `returncode` is "null when
    # the command never ran (resolvable: false)" and stdout/stderr are
    # "present only when resolvable is true" -- but nothing enforced them, so
    # a report asserting a command both never ran AND exited 0 with captured
    # output was accepted here and validated clean against the schema. For a
    # record whose entire purpose is proving months later what was checked
    # and what it said, an internally false entry is worse than a rejected
    # one. `core.gate.classify_outcome` -- the sole real producer of this
    # shape -- already satisfies both: its unresolvable branch emits
    # `returncode: None` with no stdout/stderr keys, and both resolvable
    # branches emit an int returncode with both keys present.
    present_optional = sorted(_OPTIONAL_COMMAND_KEYS & set(entry.keys()))
    if not resolvable:
        if returncode is not None:
            raise ValueError(
                f"commands[{index}] is unresolvable (resolvable: False) so 'returncode' "
                f"must be None, got {returncode!r}"
            )
        if present_optional:
            raise ValueError(
                f"commands[{index}] is unresolvable (resolvable: False) so it must carry "
                f"no {present_optional} -- a command that never ran captured no output"
            )
    elif returncode is None:
        raise ValueError(
            f"commands[{index}] is resolvable (resolvable: True) so 'returncode' must be "
            "an int, got None"
        )
    return dict(entry)


def build_gate_record(
    *,
    story_key: str,
    commands: Sequence[Mapping[str, object]],
    scope_check_verdict: str | None,
    tree_revision: str,
    timestamp: str,
) -> dict[str, object]:
    """Shape an already-completed gate evaluation's facts into the dict
    ``schemas/gate-record.json`` describes (Story 2.6). Every argument is a
    fact the caller already gathered -- this function does no I/O, no VCS
    call, no clock read (AD-4), mirroring ``classify_outcome``'s own
    "already-obtained outcome" shape throughout this package.

    ``story_key`` is canonicalized via ``core.identity.normalize()`` (AD-23
    -- the one parser) and stored under the OUTPUT key ``"story"``, not
    ``"story_key"`` (review finding, verified live: ``"story_key"`` itself
    ends in the ``_KEY`` suffix ``core.policy.is_secret_key`` matches, so
    every real ``to_redacted(build_gate_record(...))`` call redacted the
    record's own story identifier to ``***REDACTED***`` -- silently
    defeating "retrievable per story", the AC this field exists for. The
    PARAMETER stays named ``story_key`` -- only the emitted dict key
    changed). Each ``commands``
    entry is validated by ``_validate_command_report``. ``scope_check_verdict``
    must be ``None`` or one of ``core.model.Verdict``'s 6 values (Story 2.3
    does not exist yet, so ``None`` is the only value any real caller can
    supply today). ``tree_revision`` must be a non-empty ``str``.
    ``timestamp`` must be a UTC ISO-8601 string, validated via ``datetime.
    fromisoformat`` with a zero tz offset AND against ``_TIMESTAMP_PATTERN``
    -- the schema's own spelling, since `fromisoformat` accepts several
    legitimate forms `schemas/gate-record.json` does not (review finding;
    see that constant). PARSING only, this function never calls
    ``datetime.now()`` (AD-4 stays clock-free).

    Raises ``ValueError`` (or ``MalformedStoryKeyError``, a ``ValueError``
    subclass) for any malformed input -- a caller bug, not a real-world
    outcome to report as a ``Finding``; see the module docstring."""
    key = identity.normalize(story_key)

    if isinstance(commands, str):
        raise ValueError(
            f"commands must be a sequence of command reports, not a bare str: {commands!r}"
        )
    if not isinstance(commands, Sequence):
        raise ValueError(f"commands must be a Sequence, got {commands!r}")
    command_reports = [
        _validate_command_report(entry, index) for index, entry in enumerate(commands)
    ]

    if scope_check_verdict is not None:
        try:
            Verdict(scope_check_verdict)
        except ValueError as exc:
            raise ValueError(
                "scope_check_verdict must be None or one of "
                f"{sorted(member.value for member in Verdict)}, got {scope_check_verdict!r}"
            ) from exc

    # `.strip()`, not `== ""` (follow-up review finding, verified live): a
    # whitespace-only revision was accepted, so the record identified the
    # evaluated tree state with `"   "`.
    if not isinstance(tree_revision, str) or not tree_revision.strip():
        raise ValueError(f"tree_revision must be a non-blank str, got {_safe_repr(tree_revision)}")

    if not isinstance(timestamp, str):
        raise ValueError(f"timestamp must be a str, got {type(timestamp).__name__}")
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ValueError(
            f"timestamp must be a valid ISO-8601 string, got {timestamp!r}"
        ) from exc
    offset = parsed.utcoffset()
    # Two distinct messages (review finding): `offset is None` means no
    # timezone was attached at all (the most likely real-world mistake --
    # forgetting `+00:00`/`Z`), which is a materially different fix from a
    # timestamp that DOES carry a timezone, just not UTC. The prior single
    # message ("must be UTC (zero tz offset)") was technically true either
    # way but pointed a caller who forgot a timezone entirely toward the
    # wrong diagnosis.
    if offset is None:
        raise ValueError(
            f"timestamp must include a UTC timezone (e.g. a 'Z' suffix or "
            f"'+00:00'), got {timestamp!r}"
        )
    if offset != timedelta(0):
        raise ValueError(f"timestamp must be UTC (zero tz offset), got {timestamp!r}")
    # Last, so the two more specific diagnostics above still win for the
    # mistakes they name. See `_TIMESTAMP_PATTERN`: everything reaching here
    # is already a valid UTC ISO-8601 instant, but only the schema's own
    # canonical spelling may be EMITTED, or the record fails the contract it
    # is written against.
    if not _TIMESTAMP_PATTERN.match(timestamp):
        # The message names what the pattern ACTUALLY accepts (follow-up
        # review finding): it also permits a space in place of the `T` and
        # any number of fractional digits, so the previous, narrower wording
        # left a caller unable to predict which inputs would be taken.
        raise ValueError(
            "timestamp must use schemas/gate-record.json's canonical UTC ISO-8601 "
            "spelling, YYYY-MM-DD, then 'T' or a space, then HH:MM:SS with optional "
            "fractional seconds, then 'Z' or '+00:00' (seconds are required, every "
            "component must be in range, and the offset may not be abbreviated), got "
            f"{timestamp!r}"
        )

    return {
        "story": str(key),
        "commands": command_reports,
        "scope_check_verdict": scope_check_verdict,
        "tree_revision": tree_revision,
        "timestamp": timestamp,
    }
