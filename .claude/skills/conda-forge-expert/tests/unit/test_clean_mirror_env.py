"""Regression guard for the `clean_mirror_env` fixture (tests/conftest.py).

The host-gate tests assert exact allowlist sets, and the allowlist is derived
from every set `*_BASE_URL` var. On 2026-09-29 a local `pr-preflight` failed
because a Claude Code shell exports `ANTHROPIC_BASE_URL`, which put
`api.anthropic.com` into the set. CI has no such var, so without this file
nothing in CI would notice the fixture stop working.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture
def _ambient_mirror_vars(monkeypatch):
    """What a developer shell might export before the test starts. Requested
    ahead of `clean_mirror_env` below, so it is set when the fixture runs."""
    monkeypatch.setenv("SOME_TOOL_BASE_URL", "https://api.stray-tool.example/v1")
    monkeypatch.setenv("npm_config_registry", "https://npm.stray-tool.example/")
    monkeypatch.setenv("NPM_CONFIG_REGISTRY", "https://npm.stray-tool.example/")


def test_removes_ambient_base_url_and_npm_registry_vars(_ambient_mirror_vars, clean_mirror_env):
    assert [k for k in os.environ if k.endswith("_BASE_URL")] == []
    assert "npm_config_registry" not in os.environ
    assert "NPM_CONFIG_REGISTRY" not in os.environ


def test_fallback_allowlist_is_empty_despite_an_ambient_base_url(
    _ambient_mirror_vars, clean_mirror_env, load_module
):
    """The exact shape of the 2026-09-29 failure, with a stand-in host."""
    mod = load_module("inventory_channel.py")
    assert mod._fallback_configured_enterprise_hosts() == set()
