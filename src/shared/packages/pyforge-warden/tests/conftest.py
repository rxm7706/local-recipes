"""Shared test fixtures (Story 1.1).

``make_component`` is the single Component factory for the whole suite,
exposed via the ``component_factory`` fixture — test modules take the
fixture instead of importing across test files.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

from pyforge.warden.inventory import (
    Component,
    Provenance,
    PypiIdentity,
    derive_purl,
)
from pyforge.warden.models import (
    CveMatchLevel,
    Ecosystem,
    ExtractionMode,
    IdentitySource,
    WithholdReason,
)

_UNSET: Any = object()


def make_component(
    name: str = "requests",
    version: str | None = "2.31.0",
    ecosystem: Ecosystem = Ecosystem.PYPI,
    *,
    provenance: tuple[tuple[str, str], ...] = (("pyproject.toml", "dependencies"),),
    purl: str | None = None,
    cve_match_level: CveMatchLevel | None = None,
    indeterminate_reason: WithholdReason | None = None,
    pypi_identity: PypiIdentity | None = _UNSET,
    identity_source: IdentitySource = IdentitySource.NATIVE,
    mapping_confidence: str | None = None,
    extraction_mode: ExtractionMode = ExtractionMode.PARSED,
    hygiene_covered: bool = True,
    vuln_matchable: bool | None = None,
) -> Component:
    has_version = bool(version)  # "" is version-less, same as None
    if cve_match_level is None:
        cve_match_level = (
            CveMatchLevel.EXACT if has_version else CveMatchLevel.NAME_ONLY
        )
    if pypi_identity is _UNSET:
        pypi_identity = PypiIdentity(name=name, version=version)
    if vuln_matchable is None:
        # The Gap-C predicate (enforced by Component.__post_init__).
        vuln_matchable = (
            has_version and pypi_identity is not None and indeterminate_reason is None
        )
    return Component(
        name=name,
        version=version,
        ecosystem=ecosystem,
        pypi_identity=pypi_identity,
        identity_source=identity_source,
        mapping_confidence=mapping_confidence,
        cve_match_level=cve_match_level,
        extraction_mode=extraction_mode,
        purl=purl if purl is not None else derive_purl(ecosystem, name, version),
        provenance=tuple(Provenance(manifest=m, section=s) for m, s in provenance),
        hygiene_covered=hygiene_covered,
        vuln_matchable=vuln_matchable,
        indeterminate_reason=indeterminate_reason,
    )


@pytest.fixture
def component_factory():
    """The shared ``Component`` factory (a plain function; see
    ``make_component``)."""
    return make_component


# --- Story 1.2: deny-by-default socket harness (C0c / NFR-S2) ---------------
#
# EVERY test in the suite (unit + meta + conformance, present and future)
# runs with outbound egress primitives patched to raise — no allowlist.
# The patches are applied at conftest IMPORT time (module level, below) and
# are deliberately NEVER undone: a fixture would only cover the
# test-execution window, leaving test-module IMPORT-time egress unpatched.
# NFR-S2's boundary is the orchestrator PROCESS: engine subprocesses
# (1.3+) are naturally outside in-process patching, matching the PRD's
# "network is confined to the named engine subprocesses".
#
# Denied primitives: socket.socket.{connect, connect_ex, sendto, sendmsg},
# socket.create_connection, and the FULL resolver family socket.
# {getaddrinfo, gethostbyname, gethostbyname_ex, gethostbyaddr,
# getnameinfo} — name resolution (forward AND reverse) is egress too.
#
# Stated bounds (not aspirational):
# * code reaching for the private ``_socket`` C module directly bypasses
#   these module-level patches — the package imports only the public
#   ``socket`` surface (and 1.2 imports none at all);
# * a module imported BEFORE this conftest that captured a primitive by
#   value (``from socket import create_connection``) holds the unpatched
#   function — the patches rebind the module/class attributes, not
#   pre-existing references;
# * ``send``/``sendall`` on an ALREADY-ESTABLISHED socket (``fromfd`` on an
#   inherited descriptor, ``socketpair`` IPC) are not denied: in-process
#   connection ESTABLISHMENT is impossible under the connect/sendto
#   denials, and inherited descriptors cross the process boundary this
#   harness polices.
# jsonschema/importlib.resources call none of the denied primitives, so
# the suite stays offline-green.
#
# BLAST RADIUS (deliberate, process-global): any pytest invocation whose
# collection imports this conftest denies egress for EVERY test that runs
# afterwards in the same interpreter — including OTHER suites in this
# monorepo (e.g. the conda-forge-expert suite's real-network tests). Run
# this package's suite via its own pixi task (the loop's verify gate does);
# do not collect it together with network-dependent suites in one process.
#
# The error deliberately subclasses RuntimeError, NOT OSError: code under
# test that gracefully catches socket/OSError failures must NOT be able to
# swallow the denial — egress is a hard test failure, not a degraded path.
# Tests reach the class via the ``socket_deny_error`` fixture below (never a
# cross-test-file import).

import socket


class SocketDenyError(RuntimeError):
    """Raised when any test attempts outbound network egress (C0c/NFR-S2)."""

    def __init__(self, primitive: str, destination: object) -> None:
        super().__init__(
            f"outbound network egress denied by the C0c test harness: "
            f"{primitive} -> {destination!r} (NFR-S2: deny-by-default, "
            f"no allowlist)"
        )
        self.primitive = primitive
        self.destination = destination


def _denied_connect(self, address, *args, **kwargs):
    raise SocketDenyError("socket.socket.connect", address)


def _denied_connect_ex(self, address, *args, **kwargs):
    raise SocketDenyError("socket.socket.connect_ex", address)


def _denied_sendto(self, data, *args, **kwargs):
    # sendto(bytes, address) or sendto(bytes, flags, address): the
    # destination is the LAST positional argument (the primitive is
    # C-implemented, so it can never arrive as a keyword).
    raise SocketDenyError("socket.socket.sendto", args[-1] if args else None)


def _denied_sendmsg(self, *args, **kwargs):
    # sendmsg(buffers[, ancdata[, flags[, address]]]): the destination is
    # the optional 4th positional argument (None on a connected socket).
    raise SocketDenyError(
        "socket.socket.sendmsg", args[3] if len(args) >= 4 else None
    )


def _denied_create_connection(address, *args, **kwargs):
    raise SocketDenyError("socket.create_connection", address)


def _denied_getaddrinfo(host, port, *args, **kwargs):
    raise SocketDenyError("socket.getaddrinfo", (host, port))


def _denied_gethostbyname(hostname):
    raise SocketDenyError("socket.gethostbyname", hostname)


def _denied_gethostbyname_ex(hostname):
    raise SocketDenyError("socket.gethostbyname_ex", hostname)


def _denied_gethostbyaddr(ip_address):
    raise SocketDenyError("socket.gethostbyaddr", ip_address)


def _denied_getnameinfo(sockaddr, flags):
    # Reverse DNS is resolver egress too — the fifth member of the family.
    raise SocketDenyError("socket.getnameinfo", sockaddr)


# Applied at IMPORT time; deliberately never unpatched (see block comment).
socket.socket.connect = _denied_connect
socket.socket.connect_ex = _denied_connect_ex
socket.socket.sendto = _denied_sendto
socket.socket.sendmsg = _denied_sendmsg
socket.create_connection = _denied_create_connection
socket.getaddrinfo = _denied_getaddrinfo
socket.gethostbyname = _denied_gethostbyname
socket.gethostbyname_ex = _denied_gethostbyname_ex
socket.gethostbyaddr = _denied_gethostbyaddr
socket.getnameinfo = _denied_getnameinfo


@pytest.fixture
def socket_deny_error() -> type[SocketDenyError]:
    """The harness's denial error class, exposed as a fixture (mirrors
    ``component_factory``: test modules take the fixture instead of
    importing across test files)."""
    return SocketDenyError


# --- Story 1.5: ambient osv-scanner offline DB (keeps pre-1.5 fixtures green) -
#
# ``engines.OsvEngine`` is now live in the registry, so ANY test that invokes
# ``cli.main`` (or ``OsvEngine.run``) for real against a vuln-matchable
# component (an ==-pinned PyPI dependency) spawns a REAL osv-scanner
# subprocess. Pre-1.5 fixtures/tests (``requests==2.31.0`` etc.) were
# authored assuming vulnerability-axis silence — no engine had ever consulted
# a DB, so those scans read "clean" trivially. Rather than rewrite every one
# of them into an osv conformance test, EVERY test gets a harmless,
# content-valid offline OSV database by default (an autouse fixture) so a
# scan of an ordinary pinned dependency reads genuinely clean (osv ran,
# consulted a real DB, found nothing) instead of
# ``indeterminate:offline-db-unavailable:*``. Tests that specifically
# exercise the DB-absent/corrupt/vulnerable-pin paths override the env var
# themselves (``monkeypatch.setenv``/``delenv`` in the test body composes
# with — and wins over — this fixture's own ``setenv``, since the test body
# runs after fixture setup).
#
# The DB is built ONCE per test session (osv-scanner never mutates its own
# offline cache) from the SAME Story 1.4 fixture records
# (``tests/fixtures/osv-db/pypi``) — its one seeded advisory
# (``PDOS-FIXTURE-0001``, package ``pdos-vuln-fixture``) never collides with
# any real-world package name the fixture projects declare.


def _load_osv_db_builder():
    """Import ``fixtures/osv_db_builder`` by path (the fixtures dir is data,
    not an importable package) — mirrors
    ``test_osv_offline_db_spike.py``'s ``_load_builder()``."""
    module_path = Path(__file__).resolve().parent / "fixtures" / "osv_db_builder.py"
    spec = importlib.util.spec_from_file_location("osv_db_builder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def _osv_ambient_cache_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    builder = _load_osv_db_builder()
    records_dir = Path(__file__).resolve().parent / "fixtures" / "osv-db" / "pypi"
    cache_root = tmp_path_factory.mktemp("osv-ambient-cache")
    return builder.build_offline_db(records_dir, cache_root)


@pytest.fixture(autouse=True)
def _osv_ambient_db_env(
    monkeypatch: pytest.MonkeyPatch, _osv_ambient_cache_root: Path
) -> None:
    monkeypatch.setenv(
        "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", str(_osv_ambient_cache_root)
    )
