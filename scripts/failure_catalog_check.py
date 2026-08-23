#!/usr/bin/env python3
"""failure-catalog-check — independently re-resolve the committed
failure-catalog.yaml's `enforced_by` pointers against the live check
registry, delegate catalog<->SKILL.md drift detection to
failure_catalog_generator.py --check (Story 7.1), and report the
null-rows backlog.

Story 7.1's `failure_catalog_generator.py` can detect catalog<->SKILL.md
drift and validate `enforced_by` pointers, but only when explicitly run
with `--check` -- nothing wires this into the repo's detector suite, and
nothing independently re-resolves a COMMITTED pointer against the live
check registry the way this script does: `recipe_optimizer.py` can drift
(a check code renamed or removed) without SKILL.md or the catalog
changing at all, and `check_pointers()` below re-derives "does this
pointer resolve?" from the pointed-at file's *current* source, on its own,
rather than trusting whatever the catalog last recorded.

Findings:
  unresolved-pointer  a committed catalog row's non-null `enforced_by`
                       pointer doesn't resolve -- its target file is
                       missing, or the pointed-at CODE is absent from
                       that file's live source.
  catalog-drift        `failure_catalog_generator.py --check` reports the
                        committed catalog is out of sync with SKILL.md.

Null rows (`enforced_by: null`) are reported as an informational
null_rows/coverage stat -- NEVER a finding, NEVER affects the exit code
(108/110 null today is the expected, honest starting state -- see
SKILL.md's "Recipe Authoring Gotchas" corpus).

Exit codes: 0 clean, 1 findings, 2 could-not-run -- the generator itself
failed on an unrecoverable/unexpected error (SKILL.md unreadable, the
generator script missing, a malformed catalog, ...), which is distinct
from an ordinary drift report and must never read as silently clean.
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked
# files only (the committed catalog + SKILL.md + recipe_optimizer.py, via
# the generator subprocess) — runs identically in CI and locally.
DETECTOR = {"scope": "repo"}

import argparse
import json
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
GENERATOR_REL = ".claude/skills/conda-forge-expert/scripts/failure_catalog_generator.py"
CATALOG_REL = ".claude/skills/conda-forge-expert/config/failure-catalog.yaml"


class CouldNotRunError(RuntimeError):
    """The detector itself could not complete a real check -- distinct from
    a `catalog-drift` finding. The generator's own `--check` exiting
    non-zero on an ordinary drift report (its "DRIFT DETECTED" message) is
    a finding; every other non-zero exit (SKILL.md unreadable, the catalog
    missing, a CatalogError, the generator script itself absent, ...) means
    the generator never got far enough to compare anything, so this is
    raised instead of being silently read as clean or folded into
    `findings`."""


def _load_catalog(path: pathlib.Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CouldNotRunError(f"cannot read {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise CouldNotRunError(f"{path}: not valid YAML: {exc}") from exc
    if not isinstance(data, dict) or "rows" not in data:
        raise CouldNotRunError(
            f"{path}: does not look like a failure-catalog.yaml (missing "
            "top-level 'rows')")
    rows = data["rows"]
    if not isinstance(rows, list):
        raise CouldNotRunError(
            f"{path}: 'rows' must be a list, got {type(rows).__name__}")
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CouldNotRunError(
                f"{path}: rows[{i}] must be a mapping, got {type(row).__name__}")
    return data


def _code_present(text: str, code: str) -> bool:
    return f'code="{code}"' in text or f"code='{code}'" in text


def check_pointers(root: pathlib.Path, rows: list[dict]) -> tuple[list[dict], int]:
    """(findings, null_rows) for the pointer-resolution lint alone -- a pure
    function of `root` + `rows`, no subprocess, no drift check -- so a
    bogus pointer or a missing target file can be proven in isolation."""
    findings: list[dict] = []
    null_rows = 0
    for row in rows:
        row_id = row.get("id", "?")
        enforced_by = row.get("enforced_by")
        if enforced_by is None:
            null_rows += 1
            continue
        path_str, sep, code = str(enforced_by).rpartition(":")
        if not sep:
            findings.append({
                "kind": "unresolved-pointer", "id": row_id,
                "detail": f"{row_id}: enforced_by {enforced_by!r} is not a "
                          "'<repo-relative-path>:<CODE>' pointer",
            })
            continue
        target = root / path_str
        if not target.is_file():
            findings.append({
                "kind": "unresolved-pointer", "id": row_id,
                "detail": f"{row_id}: enforced_by target {path_str!r} does not exist",
            })
            continue
        try:
            target_text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append({
                "kind": "unresolved-pointer", "id": row_id,
                "detail": f"{row_id}: cannot read enforced_by target {path_str!r}: {exc}",
            })
            continue
        if not _code_present(target_text, code):
            findings.append({
                "kind": "unresolved-pointer", "id": row_id,
                "detail": f"{row_id}: code {code!r} not found (live) in {path_str!r}",
            })
    return findings, null_rows


def check_drift(root: pathlib.Path) -> list[dict]:
    """`[]` when the generator confirms the committed catalog is in sync
    with SKILL.md; a single `catalog-drift` finding when it reports an
    ordinary drift. Any other non-zero exit -- the generator itself could
    not run -- raises CouldNotRunError instead, so a broken generator never
    reads as "no drift found"."""
    generator_path = root / GENERATOR_REL
    if not generator_path.is_file():
        raise CouldNotRunError(
            f"{generator_path} does not exist -- cannot delegate the drift check")
    try:
        proc = subprocess.run(
            [sys.executable, str(generator_path), "--check"],
            cwd=root, capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CouldNotRunError(
            f"failure_catalog_generator.py --check could not run: {exc}") from exc

    if proc.returncode == 0:
        return []
    if "DRIFT DETECTED" in proc.stderr:
        return [{
            "kind": "catalog-drift", "id": None,
            "detail": "failure-catalog.yaml is out of sync with SKILL.md's "
                      "gotcha corpus — regenerate with `pixi run -e "
                      "local-recipes generate-failure-catalog`.\n"
                      + proc.stderr.strip(),
        }]
    raise CouldNotRunError(
        "failure_catalog_generator.py --check exited "
        f"{proc.returncode} without reporting drift -- the generator itself "
        f"could not complete:\n{(proc.stdout + proc.stderr).strip()}")


def run() -> tuple[list[dict], dict]:
    catalog_path = ROOT / CATALOG_REL
    if not catalog_path.is_file():
        raise CouldNotRunError(f"{catalog_path} does not exist")
    catalog = _load_catalog(catalog_path)
    rows = catalog.get("rows") or []

    pointer_findings, null_rows = check_pointers(ROOT, rows)
    try:
        drift_findings = check_drift(ROOT)
    except CouldNotRunError as exc:
        # The drift check itself couldn't run -- still exit 2 (unchanged
        # contract), but don't let already-discovered pointer findings
        # vanish: attach them to the exception so main() can surface both.
        exc.pointer_findings = pointer_findings
        raise

    total = len(rows)
    stats = {
        "total_rows": total,
        "null_rows": null_rows,
        "coverage": (total - null_rows) / total if total else 0.0,
    }
    return pointer_findings + drift_findings, stats


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="failure-catalog-check",
        description="Independently re-resolve failure-catalog.yaml's "
                    "enforced_by pointers against the live check registry, "
                    "delegate catalog<->SKILL.md drift detection to "
                    "failure_catalog_generator.py --check, and report the "
                    "null-rows backlog. Exits 1 on any finding.")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    try:
        findings, stats = run()
    except CouldNotRunError as exc:
        # A pointer_findings attribute (see run()) means real
        # unresolved-pointer findings were already discovered before the
        # drift check itself failed -- surface them even though the overall
        # exit code stays 2 (could-not-run outranks a plain findings report).
        pointer_findings = getattr(exc, "pointer_findings", [])
        if args.json:
            print(json.dumps({"error": str(exc), "stats": None,
                              "findings": pointer_findings}))
        else:
            for f in pointer_findings:
                print(f"  {f['kind']}: {f['id']} — {f['detail']}")
            print(f"failure-catalog-check: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 -- defensive: an unexpected
        # error must never read as exit 1's "findings present" case.
        if args.json:
            print(json.dumps({"error": str(exc), "stats": None, "findings": []}))
        else:
            print(f"failure-catalog-check: unexpected error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"stats": stats, "findings": findings}, indent=2))
        return 1 if findings else 0

    print(f"failure-catalog-check: {stats['total_rows']} row(s) in "
          f"failure-catalog.yaml | null_rows={stats['null_rows']} "
          f"coverage={stats['coverage']:.1%}\n")
    if not findings:
        print("  clean — every non-null enforced_by pointer resolves; "
              "catalog matches SKILL.md.")
        return 0
    for f in findings:
        print(f"  {f['kind']}: {f['id']} — {f['detail']}")
    print(f"\nFAIL: {len(findings)} finding(s). Non-null pointers must resolve "
          "against the live check surface; regenerate with `pixi run -e "
          "local-recipes generate-failure-catalog` after any SKILL.md gotcha "
          "edit.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
