"""Meta test — the C0c socket-deny harness is ALIVE (Story 1.2).

A dead guard is a false-green about false-greens: these tests attempt real
outbound-egress primitives (connections, datagrams, AND name resolution)
and assert the conftest harness intercepts each one — including at test-
module IMPORT time, since the harness patches at conftest import, never
via a fixture window. The denial error class reaches this module via the
``socket_deny_error`` fixture (mirroring ``component_factory``) — never a
cross-test-file import.

Port 9 (discard) on 127.0.0.1 is used so that even if the guard were dead,
no meaningful egress would occur.
"""

from __future__ import annotations

import socket

import pytest

# Import-time probe: conftest patches at IMPORT time, so egress attempted
# while THIS module is still being imported must already be denied. The
# denial class is only reachable via the fixture, so RuntimeError (its
# base) is caught here; an OSError would mean REAL resolution was tried.
try:
    socket.gethostbyname("harness-import-time-probe.invalid")
except RuntimeError:
    _DENIED_AT_IMPORT_TIME = True
except OSError:  # pragma: no cover — would mean the guard is dead
    _DENIED_AT_IMPORT_TIME = False
else:  # pragma: no cover — would mean the guard is dead
    _DENIED_AT_IMPORT_TIME = False


def test_harness_denies_egress_at_module_import_time():
    """Module-level patching, not fixture patching: import-time egress from
    any test module is inside the deny boundary."""
    assert _DENIED_AT_IMPORT_TIME


def test_create_connection_is_denied(socket_deny_error):
    with pytest.raises(socket_deny_error):
        socket.create_connection(("127.0.0.1", 9))


def test_raw_socket_connect_is_denied(socket_deny_error):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with pytest.raises(socket_deny_error):
            sock.connect(("127.0.0.1", 9))


def test_connect_ex_is_denied(socket_deny_error):
    """connect_ex returns an errno instead of raising — a guard that missed
    it would let egress hide behind a return code."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with pytest.raises(socket_deny_error):
            sock.connect_ex(("127.0.0.1", 9))


def test_udp_sendto_is_denied(socket_deny_error):
    """UDP needs no connect: sendto is its own egress primitive."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        with pytest.raises(socket_deny_error):
            sock.sendto(b"x", ("127.0.0.1", 9))


def test_udp_sendmsg_is_denied(socket_deny_error):
    """sendmsg needs no connect either — a datagram socket can address the
    destination directly through it."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        with pytest.raises(socket_deny_error):
            sock.sendmsg([b"x"], [], 0, ("127.0.0.1", 9))


def test_getaddrinfo_is_denied(socket_deny_error):
    """Name resolution is egress: getaddrinfo must be intercepted."""
    with pytest.raises(socket_deny_error):
        socket.getaddrinfo("example.invalid", 443)


def test_gethostbyname_is_denied(socket_deny_error):
    with pytest.raises(socket_deny_error):
        socket.gethostbyname("example.invalid")


def test_denial_error_carries_the_destination(socket_deny_error):
    with pytest.raises(socket_deny_error) as excinfo:
        socket.create_connection(("127.0.0.1", 9))
    assert excinfo.value.destination == ("127.0.0.1", 9)
    assert "127.0.0.1" in str(excinfo.value)


def test_denial_error_is_not_an_os_error(socket_deny_error):
    """The denial must not be swallowable by graceful socket-error handling
    (except OSError) in code under test — egress is a HARD failure."""
    assert not issubclass(socket_deny_error, OSError)
