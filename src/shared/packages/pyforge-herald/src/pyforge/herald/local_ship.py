"""Local loopback caller for one real landing ship (Story 19.2).

Derives station and story from ``pyforge.core.landing_evidence``, signs
payloads the way ``webhook.verify_signature`` accepts, and POSTs them to a
loopback Herald webhook host. Not a ``herald`` CLI verb — operator-run via
``pixi run -e pyforge-foundry-full-stack herald-ship-local``.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pyforge.core import landing_evidence, roster

_MERGE_SUBJECT_TEMPLATE = "Merge {slug}/{key} into main"
_DEFAULT_REPO = "rxm7706/local-recipes"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(frozen=True)
class LandingCommit:
    sha: str
    subject: str
    station: str
    story_key: str


def _is_loopback_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return host in _LOOPBACK_HOSTS


def _sign(secret: bytes, timestamp: str, body: bytes) -> str:
    digest = hmac.new(secret, timestamp.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def classify_landing_subject(subject: str) -> tuple[str, landing_evidence.StoryKeyRef] | None:
    """Return ``(short_station, key)`` when ``subject`` is a templated landing."""
    for station in roster.STATIONS:
        slug = roster.long_form(station)
        match = landing_evidence.classify_merge_subject(
            subject,
            template=_MERGE_SUBJECT_TEMPLATE,
            project_slug=slug,
        )
        if match is not None:
            return station, match.key
    return None


def resolve_landing_commit(repo_root: Path, commit: str | None) -> LandingCommit:
    if commit is not None:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%H%x09%s", commit],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            raise SystemExit(f"commit not found: {commit!r}")
        sha, subject = proc.stdout.strip().split("\t", 1)
    else:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "log", "origin/main", "-200", "--format=%H%x09%s"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise SystemExit(f"git log origin/main failed: {proc.stderr.strip()}")
        sha = subject = ""
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            candidate_sha, candidate_subject = line.split("\t", 1)
            classified = classify_landing_subject(candidate_subject)
            if classified is not None:
                sha, subject = candidate_sha, candidate_subject
                break
        if not sha:
            raise SystemExit("no landing merge subject found on origin/main (last 200 commits)")

    classified = classify_landing_subject(subject)
    if classified is None:
        raise SystemExit(f"commit subject is not a landing merge: {subject!r}")
    station, key = classified
    return LandingCommit(sha=sha, subject=subject, station=station, story_key=key.hyphen_form())


def build_on_ship_body(landing: LandingCommit) -> bytes:
    payload = {"station": landing.station, "unblock_narrative": landing.subject}
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def build_on_pr_close_body(landing: LandingCommit, *, repo: str = _DEFAULT_REPO) -> bytes:
    payload = {
        "merged": True,
        "gates_passed": True,
        "project_name": f"{landing.station} {landing.story_key}",
        "event_id": f"{repo}@{landing.sha}",
        "evidence": [
            {
                "type": "other",
                "url": f"https://github.com/{repo}/commit/{landing.sha}",
                "label": "landing commit",
            }
        ],
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def post_signed(url: str, secret: bytes, body: bytes, *, timeout: float = 120.0) -> tuple[int, dict[str, object]]:
    ts = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": _sign(secret, ts, body),
        "X-Hub-Timestamp": ts,
    }
    req = Request(url, data=body, method="POST", headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read()
    except HTTPError as exc:
        status = exc.code
        raw = exc.read()
    except URLError as exc:
        raise SystemExit(f"POST {url} failed: {exc}") from exc
    try:
        payload: dict[str, object] = json.loads(raw)
    except json.JSONDecodeError:
        payload = {"raw": raw.decode("utf-8", errors="replace")}
    return status, payload


def deliver_landing(
    base_url: str,
    secret: bytes,
    landing: LandingCommit,
) -> dict[str, object]:
    base = base_url.rstrip("/")
    on_ship_status, on_ship_body = post_signed(
        f"{base}/stations/herald/api/v1/webhooks/on-ship",
        secret,
        build_on_ship_body(landing),
    )
    on_close_status, on_close_body = post_signed(
        f"{base}/stations/herald/api/v1/webhooks/on-pr-close",
        secret,
        build_on_pr_close_body(landing),
    )
    return {
        "landing": {
            "sha": landing.sha,
            "subject": landing.subject,
            "station": landing.station,
            "story_key": landing.story_key,
        },
        "on_ship": {"status": on_ship_status, "body": on_ship_body},
        "on_pr_close": {"status": on_close_status, "body": on_close_body},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deliver one real landing to a loopback Herald webhook host.")
    parser.add_argument(
        "commit",
        nargs="?",
        help="Merge commit sha (default: newest landing merge on origin/main)",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("HERALD_WEBHOOK_URL", "http://127.0.0.1:8000"),
        help="Loopback base URL for the platform ASGI host (default HERALD_WEBHOOK_URL or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Git checkout used to resolve the landing commit (default: cwd)",
    )
    args = parser.parse_args(argv)

    secret_raw = os.environ.get("HERALD_WEBHOOK_SECRET", "")
    if not secret_raw.strip():
        print("HERALD_WEBHOOK_SECRET is unset or empty", file=sys.stderr)
        return 1
    secret = secret_raw.encode("utf-8")

    if not _is_loopback_url(args.url):
        print(f"refusing non-loopback webhook URL: {args.url!r}", file=sys.stderr)
        return 1

    landing = resolve_landing_commit(args.repo_root.resolve(), args.commit)
    result = deliver_landing(args.url, secret, landing)
    print(json.dumps(result, indent=2, sort_keys=True))

    if result["on_ship"]["status"] != 201 or result["on_pr_close"]["status"] != 201:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
