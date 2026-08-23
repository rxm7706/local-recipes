#!/usr/bin/env python3
"""Emit the platform Containerfile pip layer from pixi.toml.

Sole authority: ``[feature.platform-image-pip.pypi-dependencies]`` in the
repo-root ``pixi.toml`` (steward Story 16.1 / CAP-5). Prints pip requirement
lines to stdout for ``pip install --no-deps -r /dev/stdin`` (or a temp file).
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "pixi.toml"
FEATURE = "platform-image-pip"


def _pins() -> list[tuple[str, str, tuple[str, ...]]]:
    data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    try:
        pypi = data["feature"][FEATURE]["pypi-dependencies"]
    except KeyError as exc:
        raise SystemExit(
            f"platform_image_pip_layer: missing "
            f"[feature.{FEATURE}.pypi-dependencies] in {MANIFEST}"
        ) from exc
    out: list[tuple[str, str, tuple[str, ...]]] = []
    for name, spec in pypi.items():
        if isinstance(spec, dict):
            version = str(spec.get("version", "")).removeprefix("==")
            extras = tuple(spec.get("extras") or ())
        else:
            version = str(spec).removeprefix("==")
            extras = ()
        out.append((name, version, extras))
    return out


def _format(name: str, version: str, extras: tuple[str, ...]) -> str:
    if extras:
        return f"{name}[{','.join(extras)}]=={version}"
    return f"{name}=={version}"


def main() -> int:
    parser = argparse.ArgumentParser(prog="platform-image-pip-layer")
    parser.add_argument(
        "--check-feature",
        action="store_true",
        help="exit 0 if the pixi feature exists and has at least one pin",
    )
    args = parser.parse_args()
    pins = _pins()
    if args.check_feature:
        if not pins:
            print("platform_image_pip_layer: feature has zero pins", file=sys.stderr)
            return 1
        print(f"platform_image_pip_layer: {len(pins)} pins in [feature.{FEATURE}]")
        return 0
    for name, version, extras in pins:
        print(_format(name, version, extras))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
