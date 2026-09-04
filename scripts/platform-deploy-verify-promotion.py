#!/usr/bin/env python3
"""Story 43.4: verify a golden-path-promotion artifact covers requested digests."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _fail(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    promotion_path = Path(os.environ.get("PROMOTION_JSON", "golden-path-promotion.json"))
    if not promotion_path.is_file():
        _fail(f"promotion artifact missing: {promotion_path}")

    payload = json.loads(promotion_path.read_text(encoding="utf-8"))
    images = payload.get("images") or {}
    warden = payload.get("warden")
    if not isinstance(warden, dict):
        _fail("promotion artifact has no Warden verdict object")
    # A verdict that exists is not a verdict that passed. Platform CI records
    # whatever Warden composed (today `indeterminate`: its vulnerability axis
    # cannot yet assess conda-sourced components); only `clean` promotes.
    status = payload.get("warden_status") or (warden.get("status") or {}).get("value")
    if status != "clean":
        driver = ((warden.get("status") or {}).get("driver") or {}).get("finding_id")
        _fail(
            f"Warden verdict is {status!r}, not 'clean' (driver: {driver}); "
            "this digest does not promote",
        )

    requested = {
        "platform": os.environ.get("PLATFORM_DIGEST", "").strip(),
        "sidecar": os.environ.get("SIDECAR_DIGEST", "").strip(),
        "mcpHost": os.environ.get("MCP_HOST_DIGEST", "").strip(),
    }
    if not all(requested.values()):
        _fail(
            "PLATFORM_DIGEST, SIDECAR_DIGEST, and MCP_HOST_DIGEST env vars are required",
        )

    for key, digest in requested.items():
        recorded = (images.get(key) or {}).get("digest")
        if recorded != digest:
            _fail(
                f"{key} digest {digest!r} is not recorded in the promotion artifact "
                f"(artifact has {recorded!r})",
            )

    print("promotion artifact verified for all three digests with a clean Warden verdict")


if __name__ == "__main__":
    main()
