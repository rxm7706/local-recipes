"""The Herald exception hierarchy (Story 1.2 -- transport-scoped subset).

Every error Herald raises descends from ``HeraldError``, so a caller can
catch the whole surface with one ``except``. This story creates only the
root plus the transport branch it actually raises: the CLI-boundary catch
and the ``exit_code_for`` projection that maps these onto process exit
codes are AD-6's assignment to Story 1.4, together with the conflict /
state errors the bridge core needs. Deliberately no exit-code map here --
a half-populated map is worse than none, because a later story would have
to keep two sources of truth agreeing.

``AuthError`` is the one error with a fixed remediation: the stored
``/design-login`` credential is missing or expired, and NFR-05 forbids
Herald minting or refreshing one itself, so the message always names
``/design-login`` as the operator's next move. No error message in this
package ever carries token material.
"""

from __future__ import annotations


class HeraldError(Exception):
    """Root of every error Herald raises deliberately."""


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
