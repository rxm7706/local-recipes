#!/usr/bin/env python3
"""Story 43.4: verify a golden-path-promotion artifact covers the requested images.

Story 134.1: the artifact holds two different values per image. ``digest`` is the
registry manifest digest, recorded only after a push; ``image_id`` is the engine's
local image ID, always recorded. For each image this compares whichever the
artifact holds: the digest when one is recorded (``PLATFORM_DIGEST``,
``SIDECAR_DIGEST``, ``MCP_HOST_DIGEST``), the image ID when none is
(``PLATFORM_IMAGE_ID``, ``SIDECAR_IMAGE_ID``, ``MCP_HOST_IMAGE_ID``). A requested
digest the artifact does not hold is refused, so an image ID never passes as one.

An artifact written before Story 134.1 has no ``image_id`` key, and its ``digest``
held the image ID: it is read as an image ID, never as a registry digest.

When ``GITHUB_OUTPUT`` is set, the verified registry digests are written to it
(``platform_digest``, ``sidecar_digest``, ``mcp_host_digest``; empty where only an
image ID is recorded) with ``by_digest``, ``true`` only when all three are digests.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import NoReturn

# image key in the artifact -> (digest env var, image ID env var, workflow output name)
_IMAGES = {
    "platform": ("PLATFORM_DIGEST", "PLATFORM_IMAGE_ID", "platform_digest"),
    "sidecar": ("SIDECAR_DIGEST", "SIDECAR_IMAGE_ID", "sidecar_digest"),
    "mcpHost": ("MCP_HOST_DIGEST", "MCP_HOST_IMAGE_ID", "mcp_host_digest"),
}
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def _fail(message: str) -> NoReturn:
    print(f"::error::{message}", file=sys.stderr)
    raise SystemExit(1)


def _recorded(entry: dict[str, object]) -> tuple[str, str]:
    """The (registry digest, image ID) an artifact entry records; either may be empty."""
    digest = str(entry.get("digest") or "").strip()
    if "image_id" not in entry:
        # Before Story 134.1 the image ID was written under `digest`.
        return "", digest
    return digest, str(entry.get("image_id") or "").strip()


def _verify_image(key: str, entry: dict[str, object]) -> str:
    """Compare one image's request to the artifact; return its verified registry digest or ''."""
    digest_var, image_id_var, _ = _IMAGES[key]
    requested_digest = os.environ.get(digest_var, "").strip()
    requested_image_id = os.environ.get(image_id_var, "").strip()
    recorded_digest, recorded_image_id = _recorded(entry)

    if recorded_digest:
        if not _DIGEST.fullmatch(recorded_digest):
            _fail(
                f"{key}: the promotion artifact's digest {recorded_digest!r} is not a "
                "sha256 manifest digest",
            )
        if not requested_digest:
            _fail(
                f"{key}: the promotion artifact records a registry digest, so {digest_var} "
                "is required (an image ID does not stand in for it)",
            )
        if requested_digest != recorded_digest:
            _fail(
                f"{key} digest {requested_digest!r} is not recorded in the promotion artifact "
                f"(artifact has {recorded_digest!r})",
            )
        if requested_image_id and requested_image_id != recorded_image_id:
            _fail(
                f"{key} image ID {requested_image_id!r} is not recorded in the promotion "
                f"artifact (artifact has {recorded_image_id!r})",
            )
        return recorded_digest

    if requested_digest:
        _fail(
            f"{key}: {digest_var}={requested_digest!r} was requested, but the promotion "
            "artifact holds no registry digest for this image (nothing was pushed; it "
            f"records the image ID {recorded_image_id!r})",
        )
    if not requested_image_id:
        _fail(
            f"{key}: the promotion artifact records no registry digest, so {image_id_var} "
            "is required",
        )
    if not recorded_image_id or requested_image_id != recorded_image_id:
        _fail(
            f"{key} image ID {requested_image_id!r} is not recorded in the promotion artifact "
            f"(artifact has {recorded_image_id!r})",
        )
    return ""


def main() -> None:
    promotion_path = Path(
        os.environ.get("PROMOTION_JSON", "golden-path-promotion.json")
    )
    if not promotion_path.is_file():
        _fail(f"promotion artifact missing: {promotion_path}")

    try:
        payload = json.loads(promotion_path.read_text(encoding="utf-8"))
    except ValueError as exc:  # JSONDecodeError and UnicodeDecodeError
        _fail(f"promotion artifact is not JSON: {promotion_path}: {exc}")
    if not isinstance(payload, dict):
        _fail(f"promotion artifact is not a JSON object: {promotion_path}")
    images = payload.get("images")
    if not isinstance(images, dict):
        _fail("promotion artifact has no `images` mapping")
    warden = payload.get("warden")
    if not isinstance(warden, dict):
        _fail("promotion artifact has no Warden verdict object")
    # A verdict that exists is not a verdict that passed. Platform CI records
    # whatever Warden composed (today `indeterminate`: its vulnerability axis
    # cannot yet assess conda-sourced components); only `clean` promotes.
    warden_status = warden.get("status")
    if not isinstance(warden_status, dict):
        warden_status = {}
    status = payload.get("warden_status") or warden_status.get("value")
    if status != "clean":
        driver = warden_status.get("driver")
        finding = driver.get("finding_id") if isinstance(driver, dict) else None
        _fail(
            f"Warden verdict is {status!r}, not 'clean' (driver: {finding}); "
            "this digest does not promote",
        )

    entries: dict[str, dict[str, object]] = {}
    for key in _IMAGES:
        entry = images.get(key)
        if entry is None:
            entry = {}
        if not isinstance(entry, dict):
            _fail(f"{key}: the promotion artifact's images.{key} is not a mapping")
        entries[key] = entry
    verified = {key: _verify_image(key, entry) for key, entry in entries.items()}
    by_digest = all(verified.values())

    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"by_digest={'true' if by_digest else 'false'}\n")
            handle.writelines(
                f"{output}={verified[key]}\n" for key, (_, _, output) in _IMAGES.items()
            )

    compared = ", ".join(
        f"{key} by {'registry digest' if digest else 'image ID'}"
        for key, digest in verified.items()
    )
    print(f"promotion artifact verified with a clean Warden verdict: {compared}")
    if not by_digest:
        print(
            "an image ID names nothing a registry serves: a registry deploy needs a pushed digest",
        )


if __name__ == "__main__":
    main()
