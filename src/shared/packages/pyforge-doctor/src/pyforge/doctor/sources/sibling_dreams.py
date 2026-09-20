"""Sibling-dreams drift gather (Story 16.1 / CAP-1; re-key Story 21.3; Story 29.1).

Diffs shared Dream filenames between this repo's ``docs/dreams/`` and the one
named sibling PyForge tree (``openteams-ai/mgmt-wf-python-modernization`` —
formerly ``OpenTeams-WFT-CDO/mgmt-wf-python-modernization``, which GitHub now
only 301-redirects) on status, owner, content-hash, and title. Warn-only,
fail-open without a token or when the sibling is unreachable — but unreachable
paths emit an explicit ``sibling-dreams-unreachable`` finding rather than
silence. Never stores sibling prose — fingerprints only.

A local Dream may carry a ``sibling-acknowledged: <hash>`` frontmatter line
(Story 29.1 / CAP-82) recording the sibling ``content_hash`` an operator has
already reviewed and accepted for that Dream (e.g. expected fold fallout).
While the sibling's current hash still equals the acknowledged one, the Dream
stays silent even if it diverges on other axes; the moment the sibling's hash
moves, the finding re-fires naming both hashes. The acknowledgement lives on
the LOCAL Dream only and records a hash, never sibling content.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather",)

_SIBLING_OWNER = "openteams-ai"
_SIBLING_REPO = "mgmt-wf-python-modernization"
_SIBLING_DREAMS_PATH = "docs/dreams"
_SIBLING_FETCH_TOTAL_BUDGET_SECONDS = 10.0
_API_BASE = f"https://api.github.com/repos/{_SIBLING_OWNER}/{_SIBLING_REPO}/contents"
_COMPARED_AXES = ("status", "owner", "content_hash", "title")


class _SiblingHTTPError(Exception):
    """A sibling fetch failed with a real HTTP status (Story 29.1).

    Raised only for ``urllib.error.HTTPError`` — every other transport
    failure still falls open to ``_fetch_sibling_fingerprints`` returning
    ``None`` (unchanged from Story 16.1), so existing fail-open behavior for
    non-HTTP failures (timeouts, connection errors, malformed payloads) is
    untouched.
    """

    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


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
        return _unreachable_finding("no operator token (set GH_TOKEN or GITHUB_TOKEN to reach sibling)")
    try:
        sibling = _fetch_sibling_fingerprints(token)
    except _SiblingHTTPError as exc:
        return _unreachable_finding(f"sibling dreams fetch failed: HTTP {exc.status_code}")
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
    # Local-only bookkeeping (Story 29.1): a hash the operator has already
    # reviewed and accepted for THIS Dream's sibling counterpart. Harmless to
    # read off a sibling fingerprint too -- siblings never declare it, and
    # nothing reads this key on the sibling side. A real sha256 hex digest is
    # a str, but an all-digit one YAML-parses as an int -- coerce numeric
    # scalars back to their literal text instead of silently discarding them
    # as "no acknowledgement" (still fails toward extra warn noise, never
    # toward silence, either way).
    ack_raw = data.get("sibling-acknowledged")
    ack = str(ack_raw) if isinstance(ack_raw, (int, float)) and not isinstance(ack_raw, bool) else ack_raw
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
        "sibling_acknowledged": ack.strip() if isinstance(ack, str) else "",
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
    """List + fetch sibling dreams; return None on any failure (fail-open).

    Raises ``_SiblingHTTPError`` for a real HTTP error response (e.g. a 404
    under a moved/renamed owner) so ``_gather`` can name the status in its
    ``sibling-dreams-unreachable`` finding (Story 29.1). Every other failure
    (timeout, connection error, malformed payload) still returns ``None``,
    unchanged from Story 16.1.
    """
    try:
        listing = _http_json(
            f"{_API_BASE}/{_SIBLING_DREAMS_PATH}",
            token,
            timeout=_SIBLING_FETCH_TOTAL_BUDGET_SECONDS,
        )
    except urllib.error.HTTPError as exc:
        raise _SiblingHTTPError(exc.code) from exc
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
            text = _http_text(download, token, timeout=_SIBLING_FETCH_TOTAL_BUDGET_SECONDS)
        except urllib.error.HTTPError as exc:
            raise _SiblingHTTPError(exc.code) from exc
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
        sibling_hash = right["content_hash"]
        ack = left.get("sibling_acknowledged", "")
        if ack and ack == sibling_hash:
            # Acknowledged at the current sibling hash: silence this Dream
            # entirely (Story 29.1), regardless of which axes still differ.
            continue
        message = f"sibling dream {slug!r} diverges on " + ", ".join(axes)
        if ack:
            message += f" (acknowledged hash {ack} no longer matches current {sibling_hash})"
        elif left["status"] == "archived":
            message += " (archived)"
        findings.append(
            Finding(
                source=Source.SIBLING_DREAMS_DRIFT,
                check="sibling-dreams-drift",
                status=DoctorStatus.WARN,
                message=message,
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
                    "sibling_content_hash": sibling_hash,
                    "sibling_acknowledged": ack,
                },
            )
        )
    return tuple(findings)


# Backward-compatible alias for tests that patch internals by name.
_diff_shared_titles = _diff_shared_slugs
