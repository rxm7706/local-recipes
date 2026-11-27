"""Shared fixtures + the egress-deny harness (Story 1.2).

Herald's suite is offline by construction: an autouse fixture patches every
socket primitive an outbound call has to go through -- the three connect
paths (``socket.socket.connect``, ``socket.socket.connect_ex``,
``socket.create_connection``), the datagram path (``socket.socket.sendto``,
which needs no connect at all), and both resolvers
(``socket.getaddrinfo``, ``socket.gethostbyname``) -- so any accidental
network reach is a loud failure rather than a slow, flaky,
credential-dependent test.

The fixture also points ``HERALD_DESIGN_CREDENTIALS`` at a path under
``tmp_path`` that does not exist. Denying egress is not enough on its own:
``resolve_design_credential()`` called with no arguments would otherwise
read the developer's real ``~/.claude/.credentials.json``, so a test could
pass on this machine because a live token happened to be lying there.

Two deliberate differences from warden's harness
(``pyforge-warden/tests/conftest.py``), which patches at import time and
never unpatches:

* This one is a **fixture**, so the ``live`` marker carves a test out.
  ``test_live_design_spike.py`` is the FR-21 proof and must reach the real
  endpoint; every other test never may. Being a fixture also means
  ``monkeypatch`` restores the real primitives at teardown, so collecting
  this suite alongside another one cannot poison it.
* The denial error subclasses ``RuntimeError``, **not** ``OSError``. The
  transport maps connection failures to ``TransportUnreachableError`` by
  catching broadly, so an ``OSError``-shaped denial would be swallowed and
  reported as a tidy "endpoint unreachable" -- the escape hatch would look
  exactly like a passing test.
"""

from __future__ import annotations

import functools
import json
import re
import socket
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from pyforge.herald import auth
from pyforge.herald.transport import ToolResult
from pyforge.herald.transport.mcp_transport import CREDENTIALS_PATH_ENV

FAKE_ACCESS_TOKEN = "herald-tests-fake-not-a-real-token"
"""Obviously-fake token for every fixture. Never a real credential."""

_FAR_FUTURE_MS = 4102444800000  # 2100-01-01, epoch milliseconds


class NetworkDeniedError(RuntimeError):
    """Raised when a non-``live`` test attempts outbound network egress."""

    def __init__(self, primitive: str, destination: object) -> None:
        super().__init__(
            f"outbound network egress denied by the herald test harness: "
            f"{primitive} -> {destination!r} (mark the test 'live' if it "
            f"is genuinely meant to reach claude-design)"
        )
        self.primitive = primitive
        self.destination = destination


def _denied_connect(self: socket.socket, address: object, *args: object) -> None:
    raise NetworkDeniedError("socket.socket.connect", address)


def _denied_connect_ex(self: socket.socket, address: object, *args: object) -> None:
    raise NetworkDeniedError("socket.socket.connect_ex", address)


def _denied_sendto(self: socket.socket, data: object, *args: object, **kwargs: object) -> None:
    raise NetworkDeniedError("socket.socket.sendto", args[-1] if args else None)


def _denied_create_connection(address: object, *args: object, **kwargs: object) -> None:
    raise NetworkDeniedError("socket.create_connection", address)


def _denied_getaddrinfo(host: object, port: object, *args: object, **kwargs: object) -> None:
    raise NetworkDeniedError("socket.getaddrinfo", (host, port))


def _denied_gethostbyname(host: object, *args: object, **kwargs: object) -> None:
    raise NetworkDeniedError("socket.gethostbyname", host)


@pytest.fixture(autouse=True)
def deny_network(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Deny egress -- and real-credential reads -- for every test not
    marked ``live`` or ``live_webhook`` (Story 13.6: a real daphne
    subprocess bound to a real loopback socket, never reaching
    claude-design -- a genuinely different kind of "live", kept as its own
    marker so each marker's docstring stays literally true, but carved out
    of this same egress-deny harness for the identical reason)."""
    if request.node.get_closest_marker("live") is not None:
        return
    if request.node.get_closest_marker("live_webhook") is not None:
        return
    monkeypatch.setattr(socket.socket, "connect", _denied_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _denied_connect_ex)
    monkeypatch.setattr(socket.socket, "sendto", _denied_sendto)
    monkeypatch.setattr(socket, "create_connection", _denied_create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", _denied_getaddrinfo)
    monkeypatch.setattr(socket, "gethostbyname", _denied_gethostbyname)
    # The env-var name comes from the transport, not a literal: if the
    # override is ever renamed, this guard must move with it rather than
    # silently stop guarding.
    monkeypatch.setenv(CREDENTIALS_PATH_ENV, str(tmp_path / "no-credentials.json"))
    # Same discipline for Story 6.3's operator-role config file: a CLI-level
    # test that calls `auth.resolve_auth_context()` with no explicit
    # `config_path` (exactly what `cli.py`'s write-command handlers do) must
    # never read the developer's real `~/.herald/config` -- point the
    # module-level default at a tmp_path location that does not exist.
    monkeypatch.setattr(auth, "DEFAULT_CONFIG_PATH", tmp_path / "no-herald-config")


@pytest.fixture(autouse=True)
def status_pages_off_unless_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 42.1: the Pages build reads ``PYFORGE_STATUS_PAGES`` from the environment, so a shell
    that exported it on would change every menu and artifact test; a test that wants it sets it."""
    monkeypatch.delenv("PYFORGE_STATUS_PAGES", raising=False)


@pytest.fixture
def network_denied_error() -> type[NetworkDeniedError]:
    """The harness's denial class as a fixture -- test modules take the
    fixture rather than importing across test files (warden's convention)."""
    return NetworkDeniedError


class FakeCaller:
    """A recording ``ToolCaller``: no network, no SDK, no async.

    ``responses`` maps a tool name to the canned ``ToolResult`` it answers
    with (or to a list, consumed one per call, for a tool invoked more than
    once). An unmapped tool answers ``{}`` so a marshalling assertion does
    not have to stub a payload it does not care about -- but a tool that
    was mapped to a list and then called once too often fails loudly: a
    silent fallback to ``{}`` there would let an extra call slip past the
    very test that counted them."""

    def __init__(self, responses: Mapping[str, Any] | None = None) -> None:
        self.responses = dict(responses or {})
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call_tool(self, tool: str, arguments: Mapping[str, Any]) -> ToolResult:
        self.calls.append((tool, dict(arguments)))
        canned = self.responses.get(tool)
        if isinstance(canned, list):
            assert canned, f"FakeCaller ran out of canned {tool!r} responses on call {len(self.calls)}"
            canned = canned.pop(0)
        if canned is None:
            return ToolResult(text="{}")
        if isinstance(canned, str):
            return ToolResult(text=canned)
        return canned

    @property
    def tools(self) -> list[str]:
        return [tool for tool, _ in self.calls]

    def arguments_for(self, tool: str) -> dict[str, Any]:
        """The arguments of the single recorded call to ``tool``."""
        matches = [args for name, args in self.calls if name == tool]
        assert len(matches) == 1, f"expected exactly one {tool} call, got {matches}"
        return matches[0]


@pytest.fixture
def fake_caller():
    """Factory for a ``FakeCaller`` (a factory, not an instance, so one test
    can build several with different canned answers)."""

    def _make(responses: Mapping[str, Any] | None = None) -> FakeCaller:
        return FakeCaller(responses)

    return _make


@pytest.fixture
def credentials_file(tmp_path: Path):
    """Factory writing a fake ``~/.claude/.credentials.json``-shaped blob
    under ``tmp_path`` and returning its path.

    ``payload`` overrides the whole document (for the malformed cases);
    otherwise a well-formed ``designOauth`` block is written with an
    obviously-fake token and a far-future expiry."""

    def _write(
        *,
        access_token: str | None = FAKE_ACCESS_TOKEN,
        expires_at: object = _FAR_FUTURE_MS,
        payload: object = None,
        name: str = ".credentials.json",
        text: str | None = None,
    ) -> Path:
        path = tmp_path / name
        if text is not None:
            path.write_text(text, encoding="utf-8")
            return path
        if payload is None:
            block: dict[str, Any] = {}
            if access_token is not None:
                block["accessToken"] = access_token
            if expires_at is not None:
                block["expiresAt"] = expires_at
            payload = {"designOauth": block}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    return _write


# ---------------------------------------------------------------------------
# Stories 58.1 and 59.1: under pytest-xdist, a module fixture that builds the site is built in one worker
# ---------------------------------------------------------------------------

#: The prefix of the xdist groups of the modules that build the site or read a build. Story 58.1 put every such test
#: in one group, because every Astro build wrote the one ``docs-site/``. Since Story 59.1 each worker builds in its
#: own copy (``pages_astro.build_site_dir``), so builds in different workers run side by side, and a group only keeps
#: the tests that share a module-scoped fixture on one worker, so that fixture's build runs once.
DOCS_SITE_XDIST_GROUP = "docs-site"

#: What marks a test module as one that builds: it names the build helper, ``tests/meta/pages_astro.py``, the one
#: module that runs Astro. A module that only reads ``docs-site/``'s tracked sources, or only names its pixi tasks,
#: builds nothing and stays out. ``tests/meta/test_site_builders_share_a_worker.py`` holds the rule.
DOCS_SITE_BUILDER_RE = re.compile(r"\bpages_astro\b")


@functools.cache
def module_builds_the_site(path: str) -> bool:
    """Does the test module at ``path`` name the build helper?"""
    try:
        return bool(DOCS_SITE_BUILDER_RE.search(Path(path).read_text(encoding="utf-8")))
    except OSError:
        return False


def module_fixtures_of(item: pytest.Item) -> tuple[str, ...]:
    """The module-scoped fixtures ``item`` uses that its own module defines, sorted (Story 59.1).

    Those are what a test of a builder module shares with its neighbours: a fixture of that scope builds once per
    worker that runs one of its tests. A fixture from a conftest, or of function scope, is no reason to share a worker.
    """
    info = getattr(item, "_fixtureinfo", None)
    module = getattr(getattr(item, "module", None), "__name__", None)
    if info is None or module is None:
        return ()
    shared = set()
    for name, defs in info.name2fixturedefs.items():
        definition = defs[-1]
        if definition.scope == "module" and getattr(definition.func, "__module__", None) == module:
            shared.add(name)
    return tuple(sorted(shared))


def docs_site_groups(items: list[pytest.Item]) -> dict[str, str]:
    """The xdist group of each test that has one, by node id (Story 59.1).

    In a module that builds, the tests that share a module fixture of that module share a group, and so, through them,
    do the tests that share any fixture with those: the groups are the connected parts of the module's tests joined by
    the module fixtures they use, so each such fixture is built in one worker. A test that uses none has no group and
    goes where a worker is free. A group is named ``docs-site:<module file>:<its fixtures, sorted, joined by +>``.
    """
    by_module: dict[str, list[tuple[pytest.Item, tuple[str, ...]]]] = {}
    for item in items:
        if module_builds_the_site(str(item.path)):
            fixtures = module_fixtures_of(item)
            if fixtures:
                by_module.setdefault(str(item.path), []).append((item, fixtures))
    groups: dict[str, str] = {}
    for path, members in by_module.items():
        parent: dict[str, str] = {}

        def find(name: str) -> str:
            while parent.setdefault(name, name) != name:
                name = parent[name]
            return name

        for _item, fixtures in members:
            for other in fixtures[1:]:
                parent[find(other)] = find(fixtures[0])
        components: dict[str, set[str]] = {}
        for _item, fixtures in members:
            for name in fixtures:
                components.setdefault(find(name), set()).add(name)
        for item, fixtures in members:
            joined = "+".join(sorted(components[find(fixtures[0])]))
            groups[item.nodeid] = f"{DOCS_SITE_XDIST_GROUP}:{Path(path).name}:{joined}"
    return groups


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Put each test of a site-building module that shares a module fixture in its group (:func:`docs_site_groups`;
    ``--dist loadgroup`` reads the mark).

    ``tryfirst``: xdist appends the group to each node id in its own collection hook, so the mark must be there first,
    and pytest-split's deselection comes later, so the groups are those of the whole collection. Decided from the
    module's text and the tests' fixtures, not a hand-kept list, so a new built-site test is placed by being written.
    """
    groups = docs_site_groups(items)
    for item in items:
        group = groups.get(item.nodeid)
        if group is not None:
            item.add_marker(pytest.mark.xdist_group(group))
