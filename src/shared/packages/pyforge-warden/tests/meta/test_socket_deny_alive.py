"""Meta test — the C0c socket-deny harness is ALIVE (Story 1.2).

A dead guard is a false-green about false-greens: these tests attempt real
outbound-egress primitives (connections, datagrams, AND name resolution)
and assert the conftest harness intercepts each one — including at test-
module IMPORT time, since the harness patches at conftest import, never
via a fixture window. The denial error class reaches this module via the
``socket_deny_error`` fixture (mirroring ``component_factory``) — never a
cross-test-file import.

Every probe is harmless even if the guard were dead: connects target port
9 (discard) on 127.0.0.1, and resolver probes use ``localhost`` — resolved
from the hosts file, so a dead guard yields a local lookup, never a real
DNS query (this suite must stay egress-free in air-gapped environments
even while proving the guard broke).
"""

from __future__ import annotations

import socket

import pytest

# Import-time probe: conftest patches at IMPORT time, so egress attempted
# while THIS module is still being imported must already be denied. The
# denial class is only reachable via the fixture, so RuntimeError (its
# base) is caught here; any other outcome means the guard is dead (and
# ``localhost`` keeps even that outcome off the wire — hosts file, no DNS).
try:
    socket.gethostbyname("localhost")
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


def test_getnameinfo_is_denied(socket_deny_error):
    """Reverse DNS is resolver egress too — the fifth family member must
    not be the guard's hole."""
    with pytest.raises(socket_deny_error):
        socket.getnameinfo(("127.0.0.1", 9), 0)


def test_gethostbyname_ex_is_denied(socket_deny_error):
    """conftest patches gethostbyname_ex too; the aliveness suite must probe
    it or a dropped patch line silently re-opens forward DNS egress."""
    with pytest.raises(socket_deny_error):
        socket.gethostbyname_ex("example.invalid")


def test_gethostbyaddr_is_denied(socket_deny_error):
    """gethostbyaddr (reverse DNS) is patched in conftest; probe it so the
    guard-alive suite covers every resolver primitive the harness denies."""
    with pytest.raises(socket_deny_error):
        socket.gethostbyaddr("127.0.0.1")


def test_denial_error_carries_the_destination(socket_deny_error):
    with pytest.raises(socket_deny_error) as excinfo:
        socket.create_connection(("127.0.0.1", 9))
    assert excinfo.value.destination == ("127.0.0.1", 9)
    assert "127.0.0.1" in str(excinfo.value)


def test_denial_error_is_not_an_os_error(socket_deny_error):
    """The denial must not be swallowable by graceful socket-error handling
    (except OSError) in code under test — egress is a HARD failure."""
    assert not issubclass(socket_deny_error, OSError)
