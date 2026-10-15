#!/usr/bin/env python3
"""Write ``manifest.json`` beside a staged Kedro-Viz export (Story 30.1)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT_MARKER = Path("docs/dashboard/README.md")
_STAGED_RELATIVE = Path("docs/dashboard/kedro-viz")
_METADATA_RELATIVE = _STAGED_RELATIVE / "api" / "deploy-viz-metadata"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _REPO_ROOT_MARKER).is_file():
            return ancestor
    raise RuntimeError(
        f"viz_manifest: could not locate {_REPO_ROOT_MARKER} by walking up from {here}"
    )


def _resolve_export_commit(explicit: str | None) -> str:
    raw = (explicit or os.environ.get("GITHUB_SHA") or "").strip()
    if not raw:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(
                f"viz_manifest: git rev-parse HEAD failed: {proc.stderr.strip()}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        raw = proc.stdout.strip()
    if not _SHA_RE.fullmatch(raw):
        print(f"viz_manifest: export commit is not 40-hex lowercase: {raw!r}", file=sys.stderr)
        raise SystemExit(1)
    return raw


def _committer_date_iso_utc(sha: str) -> str:
    proc = subprocess.run(
        ["git", "show", "-s", "--format=%cI", sha],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(
            f"viz_manifest: git show committer date for {sha} failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    raw = proc.stdout.strip()
    if raw.endswith("Z"):
        return raw
    if raw.endswith("+00:00"):
        return raw[:-6] + "Z"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        print(f"viz_manifest: unparseable committer date {raw!r}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_kedro_viz_version(metadata_path: Path) -> str:
    if not metadata_path.is_file():
        print(f"viz_manifest: missing deploy-viz-metadata: {metadata_path}", file=sys.stderr)
        raise SystemExit(1)
    try:
        document = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"viz_manifest: invalid JSON in {metadata_path}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    version = document.get("version")
    if not isinstance(version, str) or not version:
        print(f"viz_manifest: deploy-viz-metadata has no string version field: {metadata_path}", file=sys.stderr)
        raise SystemExit(1)
    return version


def write_manifest(
    staged_dir: Path,
    *,
    flag_on: bool,
    export_commit: str | None = None,
) -> int:
    """Write ``manifest.json`` under ``staged_dir`` when ``flag_on``; otherwise no-op."""
    if not flag_on:
        return 0
    staged_dir = staged_dir.resolve()
    metadata_path = staged_dir / "api" / "deploy-viz-metadata"
    kedro_viz_version = _read_kedro_viz_version(metadata_path)
    sha = _resolve_export_commit(export_commit)
    payload = {
        "export_commit": sha,
        "export_date": _committer_date_iso_utc(sha),
        "kedro_viz_version": kedro_viz_version,
    }
    out_path = staged_dir / "manifest.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Write manifest.json for a staged Kedro-Viz export.")
    parser.add_argument(
        "--staged-dir",
        type=Path,
        default=None,
        help="Staged export root (default: docs/dashboard/kedro-viz under repo root)",
    )
    parser.add_argument(
        "--flag-on",
        action=argparse.BooleanOptionalAction,
        required=True,
        help="When false, write nothing and exit 0",
    )
    parser.add_argument("--export-commit", default=None, help="40-hex SHA (default: GITHUB_SHA or HEAD)")
    args = parser.parse_args(argv)
    root = repo_root()
    staged = args.staged_dir or (root / _STAGED_RELATIVE)
    return write_manifest(staged, flag_on=args.flag_on, export_commit=args.export_commit)


if __name__ == "__main__":
    raise SystemExit(main())
