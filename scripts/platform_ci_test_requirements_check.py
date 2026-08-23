#!/usr/bin/env python3
"""platform-ci-test-requirements-check — pixi is the sole platform dep authority.

Steward Story 16.1 (CAP-5) retired ``src/platform/requirements/{base,local,production}.txt``
as an install source. ``[feature.platform-ci-test.pypi-dependencies]`` in the
repo-root ``pixi.toml`` is the CI/test authority; ``[feature.platform-image-pip]``
owns the Containerfile pip layer.

This detector fails if the retired requirement files are resurrected (so they
cannot quietly become an install authority again). It does **not** reconcile
pixi from requirements files.

Exit codes: 0 clean, 1 resurrected files found, 2 unexpected error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_DIR = REPO_ROOT / "src" / "platform" / "requirements"
FORBIDDEN = ("base.txt", "local.txt", "production.txt")
FEATURE = "platform-ci-test"


def run() -> tuple[list[dict], dict]:
    findings: list[dict] = []
    present: list[str] = []
    for name in FORBIDDEN:
        path = REQUIREMENTS_DIR / name
        if path.is_file():
            try:
                rel = str(path.relative_to(REPO_ROOT))
            except ValueError:
                rel = str(path)
            present.append(rel)
            findings.append(
                {
                    "kind": "resurrected-requirements-file",
                    "package": name,
                    "detail": (
                        f"{rel} must not exist; platform Python deps are owned by "
                        f"[feature.{FEATURE}] / [feature.platform-image-pip] in pixi.toml "
                        "(steward Story 16.1 / CAP-5)"
                    ),
                }
            )
    return findings, {
        "forbidden_files": list(FORBIDDEN),
        "resurrected": present,
        "requirements_dir": (
            str(REQUIREMENTS_DIR.relative_to(REPO_ROOT))
            if REQUIREMENTS_DIR.is_relative_to(REPO_ROOT)
            else str(REQUIREMENTS_DIR)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="platform-ci-test-requirements-check",
        description=(
            "Guard: src/platform/requirements/{base,local,production}.txt stay retired; "
            "pixi.toml is the sole platform dependency authority."
        ),
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="removed in Story 16.1 — requirements no longer drive pixi (always errors)",
    )
    args = parser.parse_args()

    if args.fix:
        msg = (
            "platform-ci-test-requirements-check: --fix was removed in steward Story 16.1; "
            "edit [feature.platform-ci-test.pypi-dependencies] in pixi.toml directly, "
            "then run `pixi lock`."
        )
        if args.json:
            print(json.dumps({"ok": False, "error": msg}))
        else:
            print(msg, file=sys.stderr)
        return 2

    try:
        findings, stats = run()
    except OSError as exc:
        print(f"platform-ci-test-requirements-check: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"ok": not findings, "findings": findings, "stats": stats}, indent=2))
    elif findings:
        print(
            "platform-ci-test-requirements-check: "
            "retired requirements files must not return:",
            file=sys.stderr,
        )
        for finding in findings:
            print(f"  - {finding['detail']}", file=sys.stderr)
        print(
            "Remedy: delete the files and keep pins in pixi.toml "
            f"([feature.{FEATURE}] / [feature.platform-image-pip]).",
            file=sys.stderr,
        )
    else:
        print(
            "platform-ci-test-requirements-check: ok — "
            "no resurrected requirements/*.txt; pixi remains sole authority"
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
