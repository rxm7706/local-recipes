"""Story 83.1 -- `keys.http_bridge()` resolves the `_http.py` bridge on first use.

Before this story `keys.py` located `_http.py`, put its directory on `sys.path`
and ran `from _http import ...` at import time. Outside a local-recipes
checkout that made `import pyforge.steward.keys` itself raise (DW-1-3-14), and
`sync.py`'s own `from _http import open_url` only worked because `keys.py` had
been imported first -- until ruff's import sort moved the `_http` import above
`from .keys import ...`. The bridge is now one cached function, called at first
use, so neither module's import depends on `_http.py` being reachable or on
import order.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pyforge.steward import keys, sync
from pyforge.steward.cli import EXIT_FAILED
from pyforge.steward.keys import HostScopedCredential, http_bridge, locate_http_module, resolve_headers

_MARKER = str(Path(".claude/skills/conda-forge-expert/scripts/_http.py"))
_GITHUB = HostScopedCredential(hosts=("api.github.com",))
_GITHUB_URL = "https://api.github.com/graphql"


@pytest.fixture(autouse=True)
def _fresh_bridge_cache():
    """`http_bridge` is `functools.cache`d; every test starts and ends cold."""
    http_bridge.cache_clear()
    yield
    http_bridge.cache_clear()


def _run_fresh(code: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run `code` in a fresh interpreter (own `sys.modules` / `sys.path`)."""
    return subprocess.run([sys.executable, "-c", code, *args], capture_output=True, text=True, check=False)


# Hides every `_http.py` from `locate_http_module`'s walk-up (`Path.is_file`) before
# either module is imported -- the shape of a package installed outside a checkout.
_HIDE_HTTP = """\
import pathlib
_real_is_file = pathlib.Path.is_file
pathlib.Path.is_file = lambda self: False if self.name == "_http.py" else _real_is_file(self)
"""


def test_import_keys_and_sync_succeed_with_no_http_module_reachable():
    code = (
        _HIDE_HTTP
        + """\
import sys
import pyforge.steward.keys
import pyforge.steward.sync
assert "_http" not in sys.modules, "an import resolved the _http bridge"
print("IMPORTED")
"""
    )

    result = _run_fresh(code)

    assert result.returncode == 0, result.stderr
    assert "IMPORTED" in result.stdout


def test_sync_imported_before_keys_still_imports_and_reconcile_does_not_crash(tmp_path):
    missing_config = tmp_path / "no-such-sync-config.yaml"
    code = """\
import sys
import pyforge.steward.sync  # first: nothing has put the _http directory on sys.path yet
from pyforge.steward.cli import main
print("RC=%d" % main(["sync", "reconcile", "--schedule", "--dry-run", "--config", sys.argv[1]]))
"""

    result = _run_fresh(code, str(missing_config))

    assert result.returncode == 0, result.stderr
    assert f"RC={EXIT_FAILED}" in result.stdout  # a named duty failure (missing config), not 70
    assert "sync config not found" in result.stderr
    assert "Traceback" not in result.stderr


def test_resolve_headers_outside_a_checkout_raises_naming_the_marker_at_first_use(tmp_path, monkeypatch):
    # `locate_http_module` walks up from `keys.__file__`; point it at a tree with no marker above it.
    monkeypatch.setattr(keys, "__file__", str(tmp_path / "pkg" / "pyforge" / "steward" / "keys.py"))

    with pytest.raises(RuntimeError, match=_MARKER.replace(".", r"\.")):
        resolve_headers(_GITHUB, _GITHUB_URL)
    # `functools.cache` does not store a raised exception: the next call re-raises it.
    with pytest.raises(RuntimeError, match=_MARKER.replace(".", r"\.")):
        resolve_headers(_GITHUB, _GITHUB_URL)


def test_bridge_is_located_once_and_sys_path_gains_the_directory_once(monkeypatch):
    scripts_dir = str(locate_http_module().parent)
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != scripts_dir])
    monkeypatch.delitem(sys.modules, "_http", raising=False)
    locate_calls: list[None] = []

    def counting_locate() -> Path:
        locate_calls.append(None)
        return locate_http_module()

    monkeypatch.setattr(keys, "locate_http_module", counting_locate)

    first = resolve_headers(_GITHUB, _GITHUB_URL)
    second = resolve_headers(_GITHUB, _GITHUB_URL)

    assert first == second
    assert len(locate_calls) == 1
    assert sys.path.count(scripts_dir) == 1
    assert http_bridge() is http_bridge()
    assert len(locate_calls) == 1


def test_sync_default_transport_goes_through_the_bridge(monkeypatch):
    """`sync.py` holds no `_http` import of its own: its transport asks `http_bridge()` at call time."""
    seen: list[tuple[object, int]] = []

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self) -> bytes:
            return b"{}"

    class _FakeBridge:
        @staticmethod
        def open_url(request, timeout=30):
            seen.append((request, timeout))
            return _Response()

    monkeypatch.setattr(sync, "http_bridge", lambda: _FakeBridge)
    request = sync.urllib.request.Request("https://api.github.com/graphql")

    response = sync._default_transport(request)

    assert response.status == 200
    assert response.body == b"{}"
    assert seen == [(request, 30)]
