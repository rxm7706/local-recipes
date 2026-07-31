"""Synthetic fixture: the pre-fix unconditional-injection shape (Story 1.2).

Reproduces the *shape* `.claude/skills/conda-forge-expert/scripts/_http.py`'s
``auth_headers_for`` had before commit ``a4137cdfa3`` added the ``skip_auth``
host-scope gate: a credential header is attached straight from an env var
with no gate that could ever depend on the target host. Structurally
similar, not a literal copy — no real secrets, and this file is never
imported, only scanned as source text by ``keys.scan_file`` in
``test_keys_audit_drift.py``.
"""

from __future__ import annotations

import os


def build_request_headers(url: str) -> dict[str, str]:
    """Pre-fix shape: nothing here can ever depend on `url`'s host."""
    headers: dict[str, str] = {}
    if os.environ.get("JFROG_API_KEY"):
        headers["X-JFrog-Art-Api"] = os.environ["JFROG_API_KEY"]
    return headers
