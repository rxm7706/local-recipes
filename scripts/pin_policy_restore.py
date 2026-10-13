#!/usr/bin/env python3
"""pin-policy-restore — rewrite pixi.toml declarations to policy clauses after an upgrade."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import pin_policy_lib as lib
from pin_policy_lib import REPO_ROOT, check_diff, check_static, load_policy

ROOT = REPO_ROOT


def _restore_clause(policy: dict, package: str, feature: str, new_floor: str, kind: str) -> str | None:
    rows = [
        h
        for h in policy.get("holds") or []
        if isinstance(h, dict)
        and h.get("package") == package
        and (h.get("features") == "*" or feature in (h.get("features") or []))
    ]
    if not rows:
        return None
    row = rows[0]
    hold = row.get("hold")
    if hold == "cap" and row.get("cap"):
        return f">={new_floor},{row['cap']}"
    if hold == "channel" and row.get("channel"):
        cap = row.get("cap") or ""
        ver = f">={new_floor}{',' + cap if cap else ''}"
        return f'{{ version = "{ver}", channel = "{row["channel"]}" }}'
    if hold == "exact" and row.get("exact"):
        ch = row.get("channel")
        if ch:
            return f'{{ version = "{row["exact"]}", channel = "{ch}" }}'
        return f'"{row["exact"]}"'
    if hold == "never-move" or hold == "floor-only":
        return f">={new_floor}"
    return None


def _toml_value(clause: str) -> str:
    stripped = clause.strip()
    if stripped.startswith("{") or stripped.startswith('"'):
        return stripped
    return f'"{stripped}"'


def _replace_declaration(text: str, package: str, new_value: str) -> str | None:
    pattern = re.compile(
        rf'^(\s*{re.escape(package)}\s*=\s*)(.+?)(\s*(?:#.*)?)$',
        re.MULTILINE,
    )
    rendered = _toml_value(new_value)

    def repl(m: re.Match[str]) -> str:
        return f"{m.group(1)}{rendered}{m.group(3)}"

    new_text, n = pattern.subn(repl, text, count=1)
    return new_text if n else None


def main() -> int:
    parser = argparse.ArgumentParser(prog="pin-policy-restore")
    parser.add_argument("--from", dest="base_ref", required=True, metavar="BASE_REF")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.root
    manifest_path = root / "pixi.toml"
    policy = load_policy(root / "docs/governance/pin-policy.yaml")
    manifest_text = manifest_path.read_text(encoding="utf-8")
    current = tomllib.loads(manifest_text)
    findings, err = check_diff(policy, args.base_ref, current, root=root)
    if err:
        print(f"cannot read base: {err}", file=sys.stderr)
        return 2
    if not findings:
        return 0

    base_manifest, _ = lib._read_manifest_at_ref(args.base_ref, root=root)
    base_index = (
        {(d.feature, d.package): d for d in lib.iter_dependency_decls(base_manifest)}
        if base_manifest
        else {}
    )

    original_bytes = manifest_path.read_bytes()
    text = manifest_text
    for f in findings:
        if f.kind not in {"lost-cap", "flattened-table", "lowered-floor", "moved-hold"}:
            continue
        base_decl = base_index.get((f.feature, f.package))
        base_spec = base_decl.spec if base_decl else ""
        clause: str | None = None
        if f.kind in {"flattened-table", "moved-hold"} and base_decl:
            clause = base_spec
        elif f.kind == "lowered-floor" and base_decl:
            m = re.search(r">=\s*(\d+(?:\.\d+)*)", base_spec)
            new_floor = m.group(1) if m else "0.0.0"
            clause = _restore_clause(policy, f.package, f.feature, new_floor, f.kind)
        else:
            m = re.search(r">=\s*(\d+(?:\.\d+)*)", f.detail.split("->")[-1])
            new_floor = m.group(1) if m else "0.0.0"
            clause = _restore_clause(policy, f.package, f.feature, new_floor, f.kind)
        if not clause:
            print(f"REFUSE: no policy clause for {f.package} @ {f.feature}", file=sys.stderr)
            return 1
        updated = _replace_declaration(text, f.package, clause)
        if updated is None:
            print(f"REFUSE: could not rewrite {f.package}", file=sys.stderr)
            return 1
        text = updated

    if args.dry_run:
        sys.stdout.write(text)
        return 0

    manifest_path.write_text(text, encoding="utf-8")
    try:
        proc = subprocess.run(
            ["pixi", "lock"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        manifest_path.write_bytes(original_bytes)
        print(f"REFUSE: pixi lock failed to run: {exc}", file=sys.stderr)
        return 1
    if proc.returncode != 0:
        manifest_path.write_bytes(original_bytes)
        err = proc.stderr.strip() or proc.stdout.strip()
        print(f"REFUSE: pixi lock: {err}", file=sys.stderr)
        return 1

    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    static = check_static(policy, manifest, manifest_path.read_text(encoding="utf-8"))
    if any(s.severity == "error" for s in static):
        manifest_path.write_bytes(original_bytes)
        print("REFUSE: post-restore check failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
