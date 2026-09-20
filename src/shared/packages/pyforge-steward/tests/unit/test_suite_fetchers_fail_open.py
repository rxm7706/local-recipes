"""``suite``'s upstream probes fail OPEN: every network or filesystem miss is
``None``, never an exception -- the pipeline-truth report degrades a cell,
it does not crash the duty (AD-8). Pins the npm / GitHub release → tags
fallback / anaconda channel fetchers and the conda-meta scan, offline, by
substituting ``urllib.request.urlopen``. Surfaced by the touched-module
coverage floor on Story 63.6 (2026-09-20): ``suite.py`` sat at 77.7% against
the 80% unit floor with the whole fetcher block unmeasured.
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest
from pyforge.steward import suite
from pyforge.steward.suite import (
    _bmad_config_keys,
    _fail_open_get_json,
    _pixi_task_declared,
    _skills_census,
    fetch_channel_version,
    fetch_github_latest,
    fetch_npm_latest,
    read_installed_version,
)


class _Resp:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._payload


def _http_error(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "err", hdrs=None, fp=None)  # type: ignore[arg-type]


def _urlopen_by_url(routes: dict[str, object]):
    """A fake ``urlopen``: an exception value is raised, anything else is
    JSON-encoded as the body; the key is a substring of the request URL."""

    def _open(request, timeout=None):  # noqa: ARG001
        url = request.full_url
        for key, value in routes.items():
            if key in url:
                if isinstance(value, BaseException):
                    raise value
                return _Resp(value if isinstance(value, bytes) else json.dumps(value).encode())
        raise AssertionError(f"unrouted url {url}")

    return _open


@pytest.fixture
def route(monkeypatch: pytest.MonkeyPatch):
    def _install(routes: dict[str, object]) -> None:
        monkeypatch.setattr("pyforge.steward.suite.urllib.request.urlopen", _urlopen_by_url(routes))

    return _install


# ── _fail_open_get_json ─────────────────────────────────────────────────────


def test_fail_open_get_json_returns_the_body_and_sends_a_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    def _open(request, timeout=None):  # noqa: ARG001
        seen.update(request.headers)
        return _Resp(b'{"ok": true}')

    monkeypatch.setattr("pyforge.steward.suite.urllib.request.urlopen", _open)
    assert _fail_open_get_json("https://example.invalid/x") == {"ok": True}
    assert seen.get("User-agent") == suite._USER_AGENT


@pytest.mark.parametrize(
    "value",
    [_http_error("u", 500), urllib.error.URLError("dns"), OSError("socket"), b"not json {"],
    ids=["http-500", "url-error", "os-error", "bad-json"],
)
def test_fail_open_get_json_is_none_on_any_miss(route, value: object) -> None:
    route({"example.invalid": value})
    assert _fail_open_get_json("https://example.invalid/x") is None


# ── npm / anaconda ──────────────────────────────────────────────────────────


def test_fetch_npm_latest_reads_version_and_quotes_scoped_names(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def _open(request, timeout=None):  # noqa: ARG001
        seen.append(request.full_url)
        return _Resp(b'{"version": "6.12.0"}')

    monkeypatch.setattr("pyforge.steward.suite.urllib.request.urlopen", _open)
    assert fetch_npm_latest("@bmad/method") == "6.12.0"
    assert seen == ["https://registry.npmjs.org/%40bmad%2Fmethod/latest"]


@pytest.mark.parametrize("body", [["a", "list"], {"name": "x"}], ids=["non-dict", "no-version"])
def test_fetch_npm_latest_fails_open(route, body: object) -> None:
    route({"registry.npmjs.org": body})
    assert fetch_npm_latest("bmad-method") is None


def test_fetch_channel_version_reads_latest_version(route) -> None:
    route({"api.anaconda.org/package/SelfExplainML/bmad-method": {"latest_version": "6.12.0"}})
    assert fetch_channel_version("bmad-method") == "6.12.0"


@pytest.mark.parametrize("body", [[], {}], ids=["non-dict", "no-latest"])
def test_fetch_channel_version_fails_open(route, body: object) -> None:
    route({"api.anaconda.org": body})
    assert fetch_channel_version("bmad-method") is None


# ── GitHub: latest release, else newest parseable tag ──────────────────────


def test_fetch_github_latest_strips_the_leading_v_from_a_release_tag(route) -> None:
    route({"/releases/latest": {"tag_name": "v6.12.0"}})
    assert fetch_github_latest("bmad-code-org/BMAD-METHOD") == "6.12.0"


def test_fetch_github_latest_falls_back_to_the_newest_parseable_tag_on_404(route) -> None:
    route({
        "/releases/latest": _http_error("u", 404),
        "/tags": [
            {"name": "v1.2.3"},
            "not-a-mapping",
            {"nope": 1},
            {"name": "nightly"},
            {"name": "1.10.0"},
            {"name": "v1.9.9"},
        ],
    })
    assert fetch_github_latest("owner/repo") == "1.10.0"


def test_fetch_github_latest_empty_tag_name_falls_through_to_tags(route) -> None:
    route({"/releases/latest": {"tag_name": "   "}, "/tags": [{"name": "v0.11.0"}]})
    assert fetch_github_latest("owner/repo") == "0.11.0"


@pytest.mark.parametrize(
    "release",
    [_http_error("u", 500), urllib.error.URLError("dns"), TimeoutError(), b"{bad json"],
    ids=["http-500", "url-error", "timeout", "bad-json"],
)
def test_fetch_github_latest_non_404_misses_do_not_consult_tags(route, release: object) -> None:
    route({"/releases/latest": release, "/tags": [{"name": "v9.9.9"}]})
    assert fetch_github_latest("owner/repo") is None


@pytest.mark.parametrize(
    "tags", [{"not": "a list"}, [{"name": "main"}, {"name": "rc"}], []],
    ids=["non-list", "no-parseable", "empty"],
)
def test_fetch_github_latest_is_none_without_a_parseable_tag(route, tags: object) -> None:
    route({"/releases/latest": _http_error("u", 404), "/tags": tags})
    assert fetch_github_latest("owner/repo") is None


# ── conda-meta scan ─────────────────────────────────────────────────────────


def test_read_installed_version_picks_the_newest_across_envs(tmp_path: Path) -> None:
    for env, files in {
        "pyforge-guild": ["bmad-method-6.11.0-h1234_0.json", "bmad-method-6.12.0-h1234_0.json", "other-1.0.0-h_0.json"],
        "local-recipes": ["bmad-method-6.9.0-h1234_0.json", "bmad-method-notes.txt", "bmad-method-6.10.0-h.json.bak"],
        "broken": [],
    }.items():
        meta = tmp_path / ".pixi" / "envs" / env / "conda-meta"
        if env != "broken":
            meta.mkdir(parents=True)
        else:
            (tmp_path / ".pixi" / "envs" / env).mkdir(parents=True)  # no conda-meta -> skipped
        for name in files:
            (meta / name).write_text("{}", encoding="utf-8")
    assert read_installed_version(tmp_path, "bmad-method") == "6.12.0"
    assert read_installed_version(tmp_path, "absent") is None


def test_read_installed_version_without_envs_dir_is_none(tmp_path: Path) -> None:
    assert read_installed_version(tmp_path, "bmad-method") is None


# ── wiring probes fail open ─────────────────────────────────────────────────


def test_skills_census_and_config_keys_fail_open(tmp_path: Path) -> None:
    assert _skills_census(tmp_path) == set()
    assert _bmad_config_keys(tmp_path) == set()
    (tmp_path / "_bmad").mkdir()
    (tmp_path / "_bmad" / "config.yaml").write_text("- a list\n", encoding="utf-8")
    assert _bmad_config_keys(tmp_path) == set()
    (tmp_path / "_bmad" / "config.yaml").write_text("bmm: {}\ncore: {}\n", encoding="utf-8")
    assert _bmad_config_keys(tmp_path) == {"bmm", "core"}
    skills = tmp_path / ".claude" / "skills"
    (skills / "bmad-spec").mkdir(parents=True)
    (skills / "stray.md").write_text("", encoding="utf-8")
    assert _skills_census(tmp_path) == {"bmad-spec"}


def test_pixi_task_declared_reads_the_bmad_ui_task_table(tmp_path: Path) -> None:
    assert _pixi_task_declared(tmp_path, "labs-install") is False
    (tmp_path / "pixi.toml").write_text("[feature.bmad-ui.tasks.labs-install]\ncmd = 'x'\n", encoding="utf-8")
    assert _pixi_task_declared(tmp_path, "labs-install") is True
    assert _pixi_task_declared(tmp_path, "other") is False
