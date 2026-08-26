"""spec-mcp-era-isolation: pin stays split; mcp-host has no FastMCP 3."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _features() -> dict:
    return tomllib.loads((REPO / "pixi.toml").read_text(encoding="utf-8"))["feature"]


def test_mcp_host_feature_has_no_fastmcp_or_langflow() -> None:
    feat = _features()["mcp-host"]
    deps = feat["dependencies"]
    assert "fastmcp" not in deps
    assert "langflow" not in deps
    assert "langflow-base" not in deps
    assert deps["mcp"].startswith(">=2")
    assert "mcp-types" in deps
    # Comments may mention FastMCP/Langflow as the reason this env exists.
    # The solver contract is the dependencies table.


def test_python_agent_platform_does_not_fold_mcp_types() -> None:
    deps = _features()["python-agent-platform"]["dependencies"]
    assert "mcp-types" not in deps
    assert "httpx2" not in deps
    assert "mcp" not in deps
