"""The Herald exception hierarchy (Story 1.2's transport branch, extended by
Story 1.4 with bridge-core's conflict branch and the exit-code projection).

Every error Herald raises descends from ``HeraldError``, so a caller can
catch the whole surface with one ``except``. Story 1.2 shipped only the root
plus the transport branch it actually raises. This story adds the three
conflict errors bridge-core raises (AD-6) and ``exit_code_for``, the sole
owner of the error-to-exit-code projection -- mirroring
``pyforge.warden.verdict.exit_code_for``'s shape: checked most-specific-first
via ``isinstance``, so a narrower subclass can be given its own entry above
a broader ancestor's without disturbing it.

``AuthError`` is the one error with a fixed remediation: the stored
``/design-login`` credential is missing or expired, and NFR-05 forbids
Herald minting or refreshing one itself, so the message always names
``/design-login`` as the operator's next move. No error message in this
package ever carries token material.
"""

from __future__ import annotations

from pyforge.core.errors import PyforgeError
from pyforge.core.verdict import dispatch_exit_code


class HeraldError(PyforgeError):
    """Root of every error Herald raises deliberately.

    Story 14.3, SPEC-pyforge-core CAP-5: re-parented to the shared
    ``PyforgeError`` marker (no ``__init__`` override on either side, so
    this changes nothing observable) -- every existing subclass re-parents
    transitively, and ``except HeraldError`` sites are unaffected."""


class TransportError(HeraldError):
    """A failure reaching or talking to the ``claude-design`` surface."""


class AuthError(TransportError):
    """No usable stored ``/design-login`` credential (absent or expired).

    Herald never refreshes or writes back a credential (NFR-05), so this is
    always terminal for the current process; the message names
    ``/design-login`` as the remediation."""


class TransportUnreachableError(TransportError):
    """The transport could not establish a session with the endpoint.

    Connection refusal, DNS failure, TLS failure, an HTTP status the SDK
    rejects, or an SDK-level protocol error -- anything that means no tool
    call was answered. Distinct from ``TransportCallError``, which means
    the server was reached and answered with an error."""


class TransportCallError(TransportError):
    """The server answered, but the tool call itself failed.

    Carries the tool name and the server's own message (e.g. ``read file:
    file not found``), so the caller can distinguish an expected miss from
    a genuine outage."""


class UnconditionalWriteError(TransportError):
    """A write was attempted without an etag precondition (FR-24).

    Raised by the adapter *before* any network call, so an unconditional
    write can never reach the server: every write-side entry must carry
    ``if_match`` (or ``leaf_if_match`` for a folder destination), with
    ``"0"`` asserting the path does not yet exist."""


class SeedConflictError(HeraldError):
    """``herald deck seed`` found Design-side edits it would clobber.

    A direct ``HeraldError`` sibling of ``TransportError``, not one of its
    subclasses: the transport answered fine, and the conflict is
    bridge-core's own interpretation of that answer (Story 1.6 defines how
    a response maps to this)."""


class PullConflictError(HeraldError):
    """``herald deck pull`` found a conflict it will not silently resolve.

    Sibling of ``TransportError`` for the same reason as
    ``SeedConflictError``: the interpretation belongs to bridge-core, not
    the transport that merely answered the call."""


class ExportConflictError(HeraldError):
    """``herald deck`` export push-back found a conflict it will not
    silently resolve.

    Sibling of ``TransportError`` for the same reason as
    ``SeedConflictError``."""


class ReadBackMismatchError(HeraldError):
    """``herald deck push --prove`` (Story 23.4, CAP-6) found a pushed
    file whose read-back, after ``deck_pipeline._strip_serve_harness``,
    does not match the bytes actually sent.

    A direct ``HeraldError`` sibling, not an ``ExportConflictError``: the
    write itself succeeded (Design accepted it), so this is not the
    per-file conflict FR-20/NFR-02 handles -- it is a verification failure
    over an already-accepted write, this story's own interpretation of a
    read-back that does not round-trip. Names every mismatched file at
    once (batched, never a bare warning); falls through to the default
    exit code (``1``)."""


class OperatorAuthorizationError(HeraldError):
    """A write subcommand (``herald success publish``, ``herald notice
    author``, ...) was attempted without a verified ``operator`` role, or
    with no auth context at all (AD-16, Story 6.3).

    Deliberately a direct ``HeraldError`` sibling, not a ``TransportError``
    subclass: an authorization refusal is this CLI's own gate, decided
    before any transport call, not something the far end reported. Falls
    through ``exit_code_for``'s map to the default exit code (``1``) --
    matching Story 6.3's AC ("no action taken, exit 1") without adding a
    map entry."""


class InvalidDateRangeError(HeraldError):
    """``--date-range`` did not parse as ``<start>..<end>`` (Story 6.2).

    Raised by the CLI's own post-parse validation, not by ``argparse``'s
    ``type=`` machinery -- the AC calls for exit code ``1`` (a data-format
    problem), which only the ``dispatch``/``exit_code_for`` path produces;
    an ``argparse`` ``type=`` failure always exits ``2`` instead. Falls
    through to the default exit code (``1``)."""


class EvidenceLinkError(HeraldError):
    """A publish-time evidence-link check failed (AD-15, Story 6.4): the
    link is unreachable, or answered outside the 200-299 range.

    Falls through to the default exit code (``1``) -- a broken evidence
    link is a usage problem for the operator to fix or remove, not a
    transport outage of Herald's own MCP connection (that stays
    ``TransportError``'s exit code ``4``)."""


class ClaimNotFoundError(HeraldError):
    """A ``herald success`` subcommand (``review``, ``publish``, ``get``,
    ``validate``) named a claim id that does not exist in the claims store
    (Story 9.1/9.3; ``.herald/herald.db`` since Story 13.3). Falls through to the default exit code (``1``) -- a
    bad claim id is a usage problem for the operator to fix, not a
    transport outage."""


class ClaimStateError(HeraldError):
    """``herald success publish`` was called on a claim that is not
    currently ``draft`` (Story 9.3) -- e.g. already ``published``. Falls
    through to the default exit code (``1``)."""


class PptxTemplateError(HeraldError):
    """``herald deck pptx-spec``/``pptx-fill``'s ``--template`` path does
    not exist, or python-pptx could not open it as a ``.pptx``/``.potx``
    (Story 15.1, CAP-1). Falls through to the default exit code (``1``) --
    a bad template path is a usage problem for the operator to fix, not a
    transport outage."""


class InvalidContentPlanError(HeraldError):
    """``herald deck pptx-fill``'s ``content_plan.json`` is malformed, or
    references a layout or placeholder idx absent from the resolved
    template, or a placeholder value that is neither a string nor a list of
    strings (Story 15.1, CAP-1). Also covers a slide entry's optional
    ``"shapes"`` list (Story 15.2, spec-pptx-custom-shapes CAP-1): a
    ``"shapes"`` value that is not
    a JSON array, an individual shape entry that is not a JSON object, an
    unknown shape ``"type"``, a missing/malformed required field for that
    type, or non-positive shape geometry. Always raised before
    ``fill_template``'s ``Presentation`` is written to disk, so no output
    file exists on this error (the I/O matrix's "No file written" rows).
    Falls through to the default exit code (``1``)."""


class PaginationStalledError(HeraldError):
    """``_windowed_read`` (CAP-2 from spec-design-sync-loop, Story 23.2)
    asked the server to resume past a window's ``last_line`` and got back
    a window whose own ``last_line`` did not advance past it (DW-FU-23-2,
    Story 23.2's Edge Case Hunter finding: the un-guarded loop would
    otherwise page the same window forever). Names the file and the
    stalled line rather than looping, warning, or silently truncating.
    Falls through to the default exit code (``1``) -- a protocol contract
    violation for the operator to escalate, not a transport outage (the
    server answered every call; its answers just never advanced)."""


_EXIT_BY_ERROR: tuple[tuple[type[HeraldError], int], ...] = (
    (SeedConflictError, 3),
    (PullConflictError, 3),
    (ExportConflictError, 3),
    (TransportError, 4),
)
"""Fixed, most-specific-first exit-code map (AD-6). Checked via
``isinstance`` in order, so ``TransportError``'s one entry covers every
existing subclass (``AuthError``, ``TransportUnreachableError``,
``TransportCallError``, ``UnconditionalWriteError``) with no entry of its
own -- adding one later only ever *adds* an isinstance entry above this
line, never renumbers an existing one. A bare ``HeraldError`` (or any
subclass this map has not yet been extended to cover) falls through to
``1``, the safety net."""


def exit_code_for(error: HeraldError) -> int:
    """Project a ``HeraldError`` to its process exit code -- sole owner of
    the mapping. Story 14.3, SPEC-pyforge-core CAP-3: the most-specific
    -first ``isinstance`` dispatch itself now delegates to
    ``pyforge.core.verdict.dispatch_exit_code`` (the generalized form of
    this exact algorithm); ``_EXIT_BY_ERROR`` (station-specific data) stays
    here.

    Fixed values: ``1`` for any other ``HeraldError`` (the safety net for a
    type this map is not yet extended to cover); ``3`` for the three
    conflict types; ``4`` for ``TransportError`` and everything under it.
    Argparse's own usage-error exit (``2``) is untouched by this map -- it
    never reaches here."""
    return dispatch_exit_code(error, _EXIT_BY_ERROR, default=1)
