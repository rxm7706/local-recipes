"""Sibling-dreams drift gather (Story 16.1 / CAP-1; re-key Story 21.3).

Diffs shared Dream filenames between this repo's ``docs/dreams/`` and the one
named sibling PyForge tree (``OpenTeams-WFT-CDO/mgmt-wf-python-modernization``)
on status, owner, content-hash, and title. Warn-only, fail-open without a token
or when the sibling is unreachable — but unreachable paths emit an explicit
``sibling-dreams-unreachable`` finding rather than silence. Never stores sibling
prose — fingerprints only.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather",)

_SIBLING_OWNER = "OpenTeams-WFT-CDO"
_SIBLING_REPO = "mgmt-wf-python-modernization"
_SIBLING_DREAMS_PATH = "docs/dreams"
_SIBLING_FETCH_TOTAL_BUDGET_SECONDS = 10.0
_API_BASE = f"https://api.github.com/repos/{_SIBLING_OWNER}/{_SIBLING_REPO}/contents"
_COMPARED_AXES = ("status", "owner", "content_hash", "title")


def gather(target: Path) -> tuple[Finding, ...]:
    """Compare local vs sibling Dream fingerprints; emit one WARN per drift."""
    return degrade_on_exception(
        Source.SIBLING_DREAMS_DRIFT,
        "sibling-dreams-drift",
        lambda: _gather(target),
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    local = _local_fingerprints(target)
    if not local:
        return ()
    token = _operator_token()
    if not token:
        return _unreachable_finding(
            "no operator token (set GH_TOKEN or GITHUB_TOKEN to reach sibling)"
        )
    sibling = _fetch_sibling_fingerprints(token)
    if sibling is None:
        return _unreachable_finding("sibling dreams fetch failed")
    return _diff_shared_slugs(local, sibling)


def _unreachable_finding(reason: str) -> tuple[Finding, ...]:
    return (
        Finding(
            source=Source.SIBLING_DREAMS_DRIFT,
            check="sibling-dreams-unreachable",
            status=DoctorStatus.WARN,
            message=f"sibling dreams tree unreachable: {reason}",
            evidence={"reason": reason},
        ),
    )


def _operator_token() -> str | None:
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def _parse_dream_fingerprint(text: str) -> dict[str, str] | None:
    """Return ``{title, status, owner, content_hash}`` or ``None`` if unusable."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    closing = next(
        (i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing is None:
        return None
    try:
        data = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    status = data.get("status")
    owner = data.get("owner")
    # Body = everything after the closing fence line (UTF-8). Empty body →
    # sha256 of b"".
    marker = "\n---\n"
    fence_idx = text.find(marker, 3)
    if fence_idx == -1:
        body_bytes = b""
    else:
        body_bytes = text[fence_idx + len(marker) :].encode("utf-8")
    return {
        "title": title.strip(),
        "status": status.strip() if isinstance(status, str) else "",
        "owner": owner.strip() if isinstance(owner, str) else "",
        "content_hash": hashlib.sha256(body_bytes).hexdigest(),
    }


def _local_fingerprints(target: Path) -> dict[str, dict[str, str]]:
    dreams_dir = target / "docs" / "dreams"
    if not dreams_dir.is_dir():
        return {}
    out: dict[str, dict[str, str]] = {}
    try:
        paths = sorted(dreams_dir.glob("*.md"))
    except OSError:
        return {}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        fp = _parse_dream_fingerprint(text)
        if fp is None:
            continue
        out[path.stem] = fp
    return out


def _fetch_sibling_fingerprints(token: str) -> dict[str, dict[str, str]] | None:
    """List + fetch sibling dreams; return None on any failure (fail-open)."""
    try:
        listing = _http_json(
            f"{_API_BASE}/{_SIBLING_DREAMS_PATH}",
            token,
            timeout=_SIBLING_FETCH_TOTAL_BUDGET_SECONDS,
        )
    except Exception:  # noqa: BLE001 -- fail-open
        return None
    if not isinstance(listing, list):
        return None
    out: dict[str, dict[str, str]] = {}
    for entry in listing:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        download = entry.get("download_url")
        if not isinstance(name, str) or not name.endswith(".md"):
            continue
        if not isinstance(download, str) or not download:
            continue
        try:
            text = _http_text(
                download, token, timeout=_SIBLING_FETCH_TOTAL_BUDGET_SECONDS
            )
        except Exception:  # noqa: BLE001 -- fail-open per file / overall
            return None
        fp = _parse_dream_fingerprint(text)
        # Discard sibling bytes immediately — only keep the fingerprint.
        del text
        if fp is None:
            continue
        out[name.removesuffix(".md")] = fp
    return out


def _http_json(url: str, token: str, *, timeout: float) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "pyforge-doctor-sibling-dreams",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _http_text(url: str, token: str, *, timeout: float) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "pyforge-doctor-sibling-dreams",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read().decode("utf-8")


def _diff_shared_slugs(
    local: dict[str, dict[str, str]],
    sibling: dict[str, dict[str, str]],
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for slug in sorted(set(local) & set(sibling)):
        left, right = local[slug], sibling[slug]
        axes = [axis for axis in _COMPARED_AXES if left[axis] != right[axis]]
        if not axes:
            continue
        findings.append(
            Finding(
                source=Source.SIBLING_DREAMS_DRIFT,
                check="sibling-dreams-drift",
                status=DoctorStatus.WARN,
                message=(
                    f"sibling dream {slug!r} diverges on " + ", ".join(axes)
                ),
                evidence={
                    "slug": slug,
                    "axes": axes,
                    "local_title": left["title"],
                    "sibling_title": right["title"],
                    "local_status": left["status"],
                    "sibling_status": right["status"],
                    "local_owner": left["owner"],
                    "sibling_owner": right["owner"],
                    "local_content_hash": left["content_hash"],
                    "sibling_content_hash": right["content_hash"],
                },
            )
        )
    return tuple(findings)


# Backward-compatible alias for tests that patch internals by name.
_diff_shared_titles = _diff_shared_slugs
