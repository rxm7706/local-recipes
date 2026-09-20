"""Story 3.7 -- `pypi_index.py`'s sole function, `version_exists()`: the
PyPI JSON-index idempotence interrogation `package.py::ship_pypi` calls
before ever attempting a `twine upload`.

`urllib.request.urlopen` is mocked at this module's own namespace
(`pyforge.mason.pypi_index.urllib.request.urlopen`, matching this suite's
established "patch on the calling module's own import namespace"
convention, e.g. `test_engines_pixi.py`'s `pyforge.mason.engines.pixi.
subprocess.run`) -- no real network access anywhere in this file (AD-16)."""

from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

from pyforge.mason import pypi_index

# --- happy path: PyPI already has this name/version --------------------------


def test_version_exists_returns_true_on_a_200_response():
    with patch(
        "pyforge.mason.pypi_index.urllib.request.urlopen",
        return_value=MagicMock(),
    ) as mock_urlopen:
        result = pypi_index.version_exists("pkg", "0.1.0")

    assert result is True
    mock_urlopen.assert_called_once()


def test_version_exists_requests_the_documented_url():
    with patch(
        "pyforge.mason.pypi_index.urllib.request.urlopen",
        return_value=MagicMock(),
    ) as mock_urlopen:
        pypi_index.version_exists("pyforge-mason", "1.2.3")

    args, kwargs = mock_urlopen.call_args
    assert args[0] == "https://pypi.org/pypi/pyforge-mason/1.2.3/json"
    assert "timeout" in kwargs


# --- conclusively absent: 404 -------------------------------------------------


def test_version_exists_returns_false_on_a_404_response():
    error = urllib.error.HTTPError(
        url="https://pypi.org/pypi/pkg/0.1.0/json",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )
    with patch("pyforge.mason.pypi_index.urllib.request.urlopen", side_effect=error):
        result = pypi_index.version_exists("pkg", "0.1.0")

    assert result is False


# --- undeterminable: everything else folds into None -------------------------


def test_version_exists_returns_none_on_a_non_404_http_error():
    error = urllib.error.HTTPError(
        url="https://pypi.org/pypi/pkg/0.1.0/json",
        code=500,
        msg="Server Error",
        hdrs=None,
        fp=None,
    )
    with patch("pyforge.mason.pypi_index.urllib.request.urlopen", side_effect=error):
        result = pypi_index.version_exists("pkg", "0.1.0")

    assert result is None


def test_version_exists_returns_none_on_a_url_error():
    with patch(
        "pyforge.mason.pypi_index.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        result = pypi_index.version_exists("pkg", "0.1.0")

    assert result is None


def test_version_exists_returns_none_on_a_bare_oserror():
    with patch(
        "pyforge.mason.pypi_index.urllib.request.urlopen",
        side_effect=OSError("boom"),
    ):
        result = pypi_index.version_exists("pkg", "0.1.0")

    assert result is None


def test_version_exists_returns_none_on_a_timeout_error():
    with patch(
        "pyforge.mason.pypi_index.urllib.request.urlopen",
        side_effect=TimeoutError("timed out"),
    ):
        result = pypi_index.version_exists("pkg", "0.1.0")

    assert result is None


def test_version_exists_never_raises_for_any_of_the_undeterminable_causes():
    """Spec I/O matrix: 'PyPI interrogation undeterminable' is data, never
    raised."""
    for exc in (
        urllib.error.URLError("dns failure"),
        OSError("boom"),
        TimeoutError("timed out"),
    ):
        with patch("pyforge.mason.pypi_index.urllib.request.urlopen", side_effect=exc):
            assert pypi_index.version_exists("pkg", "0.1.0") is None


# --- timeout plumbing ----------------------------------------------------------


def test_version_exists_uses_the_default_timeout_when_none_given():
    with patch(
        "pyforge.mason.pypi_index.urllib.request.urlopen",
        return_value=MagicMock(),
    ) as mock_urlopen:
        pypi_index.version_exists("pkg", "0.1.0")

    assert mock_urlopen.call_args.kwargs["timeout"] == pypi_index._VERSION_EXISTS_TIMEOUT_SECONDS


def test_version_exists_forwards_an_explicit_timeout():
    with patch(
        "pyforge.mason.pypi_index.urllib.request.urlopen",
        return_value=MagicMock(),
    ) as mock_urlopen:
        pypi_index.version_exists("pkg", "0.1.0", timeout=5.0)

    assert mock_urlopen.call_args.kwargs["timeout"] == 5.0
