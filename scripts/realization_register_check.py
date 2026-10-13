#!/usr/bin/env python3
"""realization-register-check — schema and coverage for docs/governance/realization-register.yaml.

Exit 0 clean, 1 findings naming the package, 2 cannot read.
"""
from __future__ import annotations

DETECTOR = {"scope": "repo"}

import argparse
import json
import sys
from pathlib import Path

import jsonschema
import yaml

from realization_register_lib import (
    REGISTER_PATH,
    SCHEMA_PATH,
    load_register,
    register_packages,
    register_rows,
    required_coverage_packages,
    validate_realize_argv,
)

ROOT = Path(__file__).resolve().parent.parent


def _validate_schema(data: object, schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return [f"schema: {e.message} at {'/'.join(str(p) for p in e.path)}" for e in errors]


def check(root: Path = ROOT) -> tuple[list[str], int]:
    reg_path = root / "docs" / "governance" / "realization-register.yaml"
    schema_path = root / "docs" / "governance" / "realization-register.schema.json"
    if not reg_path.is_file():
        return [f"cannot read {reg_path}"], 2
    if not schema_path.is_file():
        return [f"cannot read {schema_path}"], 2
    try:
        data = load_register(root)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        return [f"cannot read register: {exc}"], 2

    findings: list[str] = []
    findings.extend(_validate_schema(data, schema_path))

    by_pkg = register_packages(data)
    if len(by_pkg) != len(register_rows(data)):
        findings.append("duplicate package rows in register")

    try:
        required = required_coverage_packages(root)
    except Exception as exc:  # noqa: BLE001 — detector reports could-not-run
        return [f"cannot enumerate required packages: {exc}"], 2

    for pkg in sorted(required):
        if pkg not in by_pkg:
            findings.append(f"missing row for declared package {pkg}")

    for pkg, row in by_pkg.items():
        if (pkg.startswith("bmad-") or pkg.startswith("mybmad")) and pkg not in required:
            findings.append(f"row for undeclared bmad pin {pkg}")
        findings.extend(validate_realize_argv(row, root))

    if findings:
        return findings, 1
    return [], 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="realization-register-check")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    findings, code = check(args.root)
    if args.json:
        print(json.dumps({"findings": findings, "exit": code}, indent=2))
    else:
        for line in findings:
            print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
