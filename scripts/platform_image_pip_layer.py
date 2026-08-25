#!/usr/bin/env python3
"""Retired. Host extras are [feature.python-agent-platform.dependencies].

spec-platform-image-one-pixi-env CAP-2: this emitter must not come back as an
installer. The Containerfile no longer runs ``pip install --no-deps``.
"""
from __future__ import annotations

import sys

MSG = (
    "platform_image_pip_layer is retired (spec-platform-image-one-pixi-env). "
    "Django-host extras live on [feature.python-agent-platform.dependencies]; "
    "the image is one `pixi install --frozen -e python-agent-platform`. "
    "Do not resurrect pip --no-deps."
)


def main() -> int:
    print(MSG, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
