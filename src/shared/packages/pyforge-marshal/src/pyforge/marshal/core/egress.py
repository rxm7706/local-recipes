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
_TOKEN_SHAPE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![A-Za-z0-9_])ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?<![A-Za-z0-9_])AKIA[0-9A-Z]{16,}"),
    re.compile(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9]{20,}"),
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
        if not isinstance(self.text, str):
            raise ValueError(f"text must be a str, got {self.text!r}")


def _redact_string(value: str) -> str:
    """The shape half of redaction: replace every ``_TOKEN_SHAPE_PATTERNS``
    match with ``REDACTED_SENTINEL``, independent of whatever key (if any)
    ``value`` is stored under."""
    redacted = value
    for pattern in _TOKEN_SHAPE_PATTERNS:
        redacted = pattern.sub(REDACTED_SENTINEL, redacted)
    return redacted


def _redact(value: object) -> object:
    """Recursively walk a dict/list/scalar payload. A ``Mapping``'s
    secret-shaped keys (``policy.is_secret_key``) have their value replaced
    outright -- the field-NAME half of redaction, reusing Story 1.3's
    existing suffix vocabulary rather than inventing a second one; every
    other value recurses (a nested ``Mapping``/``list``/``tuple``) or, for a
    bare ``str``, is shape-scanned via ``_redact_string``. Every other
    scalar (int, float, bool, ``None``) passes through unchanged."""
    if isinstance(value, Mapping):
        return {
            key: (
                REDACTED_SENTINEL
                if isinstance(key, str) and is_secret_key(key)
                else _redact(inner)
            )
            for key, inner in value.items()
        }
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
        raise TypeError(f"payload must be a Mapping, got {payload!r}")
    redacted = _redact(payload)
    try:
        text = json.dumps(redacted, sort_keys=True)
    except TypeError as exc:
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


def _validate_command_report(entry: Mapping[str, object], index: int) -> dict[str, object]:
    """One ``commands`` entry must carry ``command``/``returncode``/
    ``resolvable`` -- mirrors ``core.gate.classify_outcome``'s own report
    shape -- and may additionally carry ``stdout``/``stderr`` (both, if
    present, validated as ``str``, matching the schema's own typing).  No
    other key is permitted. Returns a fresh plain ``dict`` (never an alias
    of ``entry``) -- safe to `dict()`-copy rather than deep-copy since every
    permitted key's value is now a validated immutable scalar (``str``,
    ``int``, ``bool``, or ``None``)."""
    if isinstance(entry, str) or not isinstance(entry, Mapping):
        raise ValueError(f"commands[{index}] must be a Mapping, got {entry!r}")
    missing = _REQUIRED_COMMAND_KEYS - set(entry.keys())
    if missing:
        raise ValueError(
            f"commands[{index}] is missing required key(s) {sorted(missing)}: {entry!r}"
        )
    unknown = set(entry.keys()) - _ALL_COMMAND_KEYS
    if unknown:
        raise ValueError(
            f"commands[{index}] has unknown key(s) {sorted(unknown)} -- only "
            f"{sorted(_ALL_COMMAND_KEYS)} are permitted: {entry!r}"
        )
    command = entry["command"]
    if not isinstance(command, str) or command == "":
        raise ValueError(f"commands[{index}]['command'] must be a non-empty str, got {command!r}")
    resolvable = entry["resolvable"]
    if not isinstance(resolvable, bool):
        raise ValueError(f"commands[{index}]['resolvable'] must be a bool, got {resolvable!r}")
    returncode = entry["returncode"]
    if returncode is not None and (isinstance(returncode, bool) or not isinstance(returncode, int)):
        raise ValueError(
            f"commands[{index}]['returncode'] must be an int or None, got {returncode!r}"
        )
    for key in _OPTIONAL_COMMAND_KEYS:
        if key in entry and not isinstance(entry[key], str):
            raise ValueError(
                f"commands[{index}][{key!r}] must be a str when present, got {entry[key]!r}"
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
    fromisoformat`` with a zero tz offset -- PARSING only, this function
    never calls ``datetime.now()`` (AD-4 stays clock-free).

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

    if not isinstance(tree_revision, str) or tree_revision == "":
        raise ValueError(f"tree_revision must be a non-empty str, got {tree_revision!r}")

    if not isinstance(timestamp, str):
        raise ValueError(f"timestamp must be a str, got {timestamp!r}")
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

    return {
        "story": str(key),
        "commands": command_reports,
        "scope_check_verdict": scope_check_verdict,
        "tree_revision": tree_revision,
        "timestamp": timestamp,
    }
