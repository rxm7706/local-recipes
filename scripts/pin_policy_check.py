#!/usr/bin/env python3
"""pin-policy-check — static, diff, and fan-out checks for docs/governance/pin-policy.yaml.

Exit 0 clean (warnings allowed), 1 findings, 2 unreadable inputs.
"""
from __future__ import annotations

DETECTOR = {"scope": "repo"}

import argparse
import json
import sys
import tomllib
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from pin_policy_lib import (
    MANIFEST_PATH,
    POLICY_PATH,
    REPO_ROOT,
    check_diff,
    check_fan_out,
    check_static,
    exit_code_from_findings,
    load_policy,
    render_upgrade_command,
)

ROOT = REPO_ROOT


def _print_findings(findings: list, *, as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                [
                    {
                        "kind": f.kind,
                        "package": f.package,
                        "feature": f.feature,
                        "detail": f.detail,
                        "severity": f.severity,
                    }
                    for f in findings
                ],
                indent=2,
            )
        )
        return
    for f in findings:
        prefix = "warning" if f.severity == "warning" else "error"
        print(f"[{prefix}] {f.format_line()}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="pin-policy-check")
    parser.add_argument("--check", action="store_true", help="static registry check (default)")
    parser.add_argument("--diff", metavar="BASE_REF", help="compare pixi.toml pin expressions to base ref")
    parser.add_argument("--fan-out", action="store_true", help="station package ranges vs lock")
    parser.add_argument("--render-command", action="store_true", help="print canonical pixi upgrade command")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()

    mode_check = args.check or not (args.diff or args.fan_out or args.render_command)

    if args.render_command:
        try:
            policy = load_policy(args.root / "docs/governance/pin-policy.yaml")
        except OSError as exc:
            print(f"cannot read policy: {exc}", file=sys.stderr)
            return 2
        print(render_upgrade_command(policy))
        return 0

    policy_path = args.root / "docs/governance/pin-policy.yaml"
    manifest_path = args.root / "pixi.toml"
    try:
        policy = load_policy(policy_path)
    except OSError as exc:
        print(f"cannot read registry: {exc}", file=sys.stderr)
        return 2

    if args.fan_out:
        findings = check_fan_out(args.root)
        _print_findings(findings, as_json=args.json)
        return exit_code_from_findings(findings)

    if args.diff:
        if not manifest_path.is_file():
            print(f"cannot read {manifest_path}", file=sys.stderr)
            return 2
        try:
            current = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            print(f"cannot parse pixi.toml: {exc}", file=sys.stderr)
            return 2
        findings, err = check_diff(policy, args.diff, current, root=args.root)
        if err:
            print(f"cannot read pixi.toml at {args.diff!r}: {err}", file=sys.stderr)
            return 2
        _print_findings(findings, as_json=args.json)
        return exit_code_from_findings(findings)

    if mode_check:
        if not manifest_path.is_file():
            print(f"cannot read {manifest_path}", file=sys.stderr)
            return 2
        manifest_text = manifest_path.read_text(encoding="utf-8")
        try:
            manifest = tomllib.loads(manifest_text)
        except tomllib.TOMLDecodeError as exc:
            print(f"cannot parse pixi.toml: {exc}", file=sys.stderr)
            return 2
        findings = check_static(policy, manifest, manifest_text)
        _print_findings(findings, as_json=args.json)
        return exit_code_from_findings(findings)

    return 0


if __name__ == "__main__":
    sys.exit(main())
