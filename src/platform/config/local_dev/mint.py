"""CLI entry: `python -m config.local_dev.mint <persona-key>`.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

import os
import sys

import django
import structlog

__all__ = ["main"]

logger: structlog.stdlib.BoundLogger = structlog.get_logger("config.local_dev.mint")
_USAGE = "usage: python -m config.local_dev.mint <persona-key>"


def main(argv: list[str] | None = None) -> str:
    arguments = sys.argv[1:] if argv is None else argv
    if not arguments:
        raise SystemExit(_USAGE)
    persona_key = arguments[0]

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    django.setup()

    from config.local_dev.keys import ensure_keypair  # noqa: PLC0415
    from config.local_dev.personas import UnknownPersonaError  # noqa: PLC0415
    from config.local_dev.personas import persona_keys  # noqa: PLC0415
    from config.local_dev.tokens import mint_token  # noqa: PLC0415

    keypair = ensure_keypair()
    try:
        token = mint_token(persona_key)
    except UnknownPersonaError as unknown:
        message = (
            f"no persona is declared as {persona_key!r}. "
            f"Declared personas: {', '.join(persona_keys())}"
        )
        raise SystemExit(message) from unknown
    logger.info(
        "local_dev.minting_complete", persona=persona_key, kid=keypair.kid, token=token
    )
    return token


if __name__ == "__main__":
    main()
