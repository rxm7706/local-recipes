"""The `seed` exit-code taxonomy (Story 7.2, FR-126). The closed,
six-member hierarchy and its exact exit-code table come from this story's
own epics AC, not FR-126's own text (which only requires exit codes to be
"distinct and documented per failure mode") -- FR-126 is the requirement
this AC operationalizes.

Story 7.3's `seed/fs.py` -- the never-write guard -- is blocked on exactly
this module: the architecture's Module Dependency Rules pin its import
surface as "`fs` imports nothing from the package except `errors`" (AD-61
is the never-write-guard decision itself; this exact import-direction
sentence lives in the dependency-rules list beside it, not inside AD-61's
own prose), and its `NeverWriteViolation`
is one of the six leaves defined here. Beyond `fs.py`, every later `seed`
module (`verbs/`, `cli/seed.py`) that detects a failure is expected to
raise one of these six -- but no concrete raise site is added by THIS
story (see the Never bullet on every leaf's docstring below); this module
only pins the taxonomy machinery, exactly as Story 7.4 pinned
`ManifestError` without wiring it to this taxonomy yet.

`SeedError` is the root: it mixes in this repo's shared `PyforgeError`
(Story 14.3, SPEC-pyforge-core CAP-5 convention -- `except PyforgeError`
becomes the one new sentence every station's caller gains) alongside
`Exception` directly, and requires both a `message` and a `remedy` at
construction, matching `pyforge.mason.errors.MasonError`'s own
construction-time validation precedent (NFR-M3, "remedy per finding," and
the epics AC, "every exception carries a remedy string," both read as an
invariant of the type -- not a per-call convenience left to the raise
site's discretion).

Exactly six leaf subclasses exist, one per non-success outcome the epics
AC's table names, each pinning one `exit_code` class attribute and nothing
else: `ConformanceFailure` (1), `UsageError` (2), `PreconditionFailure`
(3), `NeverWriteViolation` (4), `StateInvalid` (5), `InternalError` (10).
`0` (success) is not an exception and has no class here. The hierarchy is
deliberately flat -- one layer directly under `SeedError`, never a deeper
sub-taxonomy -- so a caller can never catch an intermediate class that
spans more than one exit code; `tests/unit/test_seed_errors.py` enumerates
`SeedError.__subclasses__()` directly (no separate registry) to keep this
closed and to fail the build the moment a seventh leaf is added without an
`exit_code`, or one reuses an existing code.

This module imports nothing from `pyforge.marshal` except (transitively,
via `pyforge.core.errors`) -- i.e. it imports `PyforgeError` and nothing
else from any `pyforge.marshal.*` module (architecture: "No upward
imports. `fs` imports nothing from the package except `errors`" --
`errors` itself is the floor of that chain and must not create a cycle
back into anything it will be imported by).

Per AD-1 (shared shapes, no behaviour), this module holds the exception
type and its validation only -- no formatting beyond `__str__`, no I/O, no
CLI exit-code dispatch (mapping a caught `SeedError` to
`sys.exit(exc.exit_code)` is a future verb/CLI story's surface).
"""

from __future__ import annotations

from typing import ClassVar

from pyforge.core.errors import PyforgeError


class SeedError(PyforgeError, Exception):
    """Root of every `seed` exception. Nothing forbids direct
    instantiation (the closed-hierarchy test below raises it directly for
    exactly that reason), but every real raise site under `seed/` is
    expected to name one of the six leaves rather than this root.

    `message` and `remedy` must both be non-blank strings; construction
    raises `ValueError` (a locally constructed value, not a `SeedError`
    itself) for either being missing or blank, mirroring `MasonError`'s
    existing "construction-time validation" convention in this codebase --
    a `remedy`-less or message-less `seed` exception is exactly the drift
    NFR-M3 and the epics AC exist to prevent.

    Story 14.3, SPEC-pyforge-core CAP-5 convention: gains `PyforgeError` as
    an ADDITIONAL base alongside `Exception` (rather than relying on
    `PyforgeError`'s own `Exception` ancestry) -- `Exception` stays
    explicit in the MRO, matching this package's existing
    `adapters.fs_local.FsError(PyforgeError, Exception)`.
    """

    #: Declared here as an unset annotation only -- every leaf below
    #: overrides it with a concrete value. Left unset on the root itself
    #: (rather than defaulted) so an accidental direct `SeedError(...)`
    #: raise site has no `exit_code` to fall back on silently.
    exit_code: ClassVar[int]

    def __init__(self, message: str, *, remedy: str) -> None:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("SeedError message must be a non-empty string: it must state what failed")
        if not isinstance(remedy, str) or not remedy.strip():
            raise ValueError("SeedError remedy must be a non-empty string: it must state what to do next (NFR-M3)")
        self.message = message
        self.remedy = remedy
        super().__init__(message, remedy)

    def __str__(self) -> str:
        return f"{self.message} (remedy: {self.remedy})"

    def __reduce__(self) -> tuple[object, tuple[object, ...]]:
        # `Exception.__reduce__` (used by both `copy.deepcopy` and
        # `pickle`) reconstructs via `cls(*self.args)` -- but `remedy` is
        # keyword-only here, so that call raises `TypeError` on every
        # deepcopy/pickle round-trip (confirmed live). Mirrors
        # `pyforge.mason.errors.CfeUnresolvedError.__reduce__`'s own fix for
        # the identical problem, generalized once on this shared root
        # (every leaf below has an identical `(message, *, remedy)`
        # signature, so one override here covers all six) instead of
        # per-leaf: return a module-level, picklable-by-reference
        # reconstructor function rather than a `lambda` -- `pickle` (unlike
        # `copy.deepcopy`) cannot serialize a `lambda`, only a name it can
        # re-import.
        return (_reconstruct_seed_error, (self.__class__, self.message, self.remedy))


def _reconstruct_seed_error(cls: type[SeedError], message: str, remedy: str) -> SeedError:
    """`SeedError.__reduce__`'s reconstructor: re-applies the keyword-only
    `remedy` a plain `cls(*args)` call cannot supply. Module-level (not a
    nested/lambda function) so `pickle` can locate it by
    `__module__`/`__qualname__`."""
    return cls(message, remedy=remedy)


class ConformanceFailure(SeedError):
    """A target repo failed conformance (HARD findings). Exit code `1`.

    No concrete raise site is added by this story -- the module that
    detects a conformance failure is a later story's surface
    (`seed/verbs/`)."""

    exit_code: ClassVar[int] = 1


class UsageError(SeedError):
    """A caller-supplied argument or flag was invalid. Exit code `2`.

    No concrete raise site is added by this story -- the module that
    validates CLI arguments is a later story's surface
    (`seed/cli/seed.py`)."""

    exit_code: ClassVar[int] = 2


class PreconditionFailure(SeedError):
    """A required precondition did not hold: a dirty worktree, a target
    that is not a git repo, or hand-edited managed content. Exit code `3`.

    No concrete raise site is added by this story -- the module that
    checks these preconditions is a later story's surface (`seed/verbs/`).
    """

    exit_code: ClassVar[int] = 3


class NeverWriteViolation(SeedError):
    """A write target matched the never-write set (Tier-0 Dreams, Tier-2
    planning artifacts, Tier-3, legacy specs, BMAD installer files;
    architecture AD-61). Exit code `4`.

    No concrete raise site is added by this story -- `seed/fs.py`, the
    never-write guard itself, is Story 7.3's surface, not this one's."""

    exit_code: ClassVar[int] = 4


class StateInvalid(SeedError):
    """`.marshal/seed-state.yml` (or other persisted `seed` state) was
    missing, unreadable, or failed its schema. Exit code `5`.

    No concrete raise site is added by this story -- the module that reads
    and validates that state is a later story's surface (`seed/state/`)."""

    exit_code: ClassVar[int] = 5


class InternalError(SeedError):
    """An unanticipated internal failure -- the catch-all for anything not
    covered by the five leaves above. Exit code `10`.

    No concrete raise site is added by this story -- the top-level
    dispatcher that catches an unanticipated failure and wraps it is a
    later story's surface (`seed/cli/seed.py`)."""

    exit_code: ClassVar[int] = 10
