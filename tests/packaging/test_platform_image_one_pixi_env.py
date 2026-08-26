"""spec-platform-image-one-pixi-env: no pip --no-deps installer."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_containerfile_has_no_pip_no_deps_layer() -> None:
    text = (REPO / "src" / "platform" / "Containerfile").read_text(encoding="utf-8")
    assert "pip install --no-deps" not in text
    assert "platform-image-pip" not in text


def test_pixi_has_no_platform_image_pip_feature() -> None:
    data = tomllib.loads((REPO / "pixi.toml").read_text(encoding="utf-8"))
    assert "platform-image-pip" not in data.get("feature", {})
    assert "platform-image-pip" not in data.get("environments", {})
    feat = data["feature"]["python-agent-platform"]
    assert "pypi-dependencies" not in feat
    conda = feat["dependencies"]
    assert "django-structlog" in conda
    assert "uvicorn-worker" in conda
    assert "mcp-types" not in conda
    assert conda["whitenoise"].startswith(">=")

    ci = data["feature"]["platform-ci-test"]
    assert "pypi-dependencies" not in ci
    ci_deps = ci["dependencies"]
    assert "redis-py" in ci_deps
    assert "redis" not in ci_deps
    assert "mcp-types" in ci_deps
    assert "factory_boy" in ci_deps


def test_pip_layer_emitter_is_tombstone() -> None:
    import subprocess

    proc = subprocess.run(
        ["python3", str(REPO / "scripts" / "platform_image_pip_layer.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "retired" in proc.stderr.lower()
