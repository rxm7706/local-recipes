#!/usr/bin/env python3
"""Story 67.2 (spec-python-foundry-cutover fnd:CAP-13): laptop SBOM gate.

Runs from ``pyforge-foundry-full`` only — never ``local-recipes``. Pixi's
``depends-on`` on ``[feature.guild-tasks.tasks.sbom-laptop-gate]`` runs
``lint-types``, ``pyforge-station-tests``, ``platform-ci-test-requirements-check``
and ``platform-policy-suite-check`` before this script; this module finishes
with a lockfile channel audit and import probes for station-critical packages.

Exit codes follow ``docs/reference/judgement-vocabulary.md`` script detectors:
0 pass, 1 findings, 2 could-not-run.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
SBOM_ENV = "pyforge-foundry-full"
FORBIDDEN_ENV = "local-recipes"

# Wheels pinned in pixi.lock with no conda-forge build (documented SBOM exceptions).
PYPI_WHEEL_ALLOWLIST = frozenset({"sqlite_vec"})

# (PyPI/normalized distribution name, import probe). Used for gap naming and live checks.
STATION_IMPORT_PROBES: tuple[tuple[str, str], ...] = (
    ("httpx", "import httpx"),
    ("pydantic", "import pydantic"),
    ("pyyaml", "import yaml"),
    ("jsonschema", "import jsonschema"),
)


def _normalize_platform(name: str) -> str:
    if name.endswith("-min"):
        return name[: -len("-min")]
    return name


def _lock_platforms() -> list[str]:
    plat = os.environ.get("PIXI_PLATFORM") or os.environ.get("CONDA_SUBDIR")
    if plat:
        return [_normalize_platform(plat)]
    return ["linux-64", "osx-arm64", "win-64"]


def assert_sbom_environment() -> str | None:
    """Return an error message when the active pixi env is not the SBOM."""
    env = (
        os.environ.get("PIXI_ENVIRONMENT_NAME")
        or os.environ.get("PIXI_ENVIRONMENT")
        or ""
    )
    if env == FORBIDDEN_ENV:
        return (
            f"refuses -e {FORBIDDEN_ENV}: the laptop gate runs from "
            f"-e {SBOM_ENV} and its layer only"
        )
    if env and env != SBOM_ENV:
        return (
            f"expected pixi environment {SBOM_ENV!r}, got {env!r} "
            f"(run: pixi run -e {SBOM_ENV} sbom-laptop-gate)"
        )
    return None


def channel_audit_findings(
    lockfile: dict,
    *,
    environment: str = SBOM_ENV,
    platforms: list[str] | None = None,
) -> list[str]:
    """Every locked conda URL must sit on the environment's declared channels."""
    try:
        env_block = lockfile["environments"][environment]
    except KeyError:
        return [f"pixi.lock has no environment {environment!r}"]

    declared = [
        ch["url"].rstrip("/")
        for ch in (env_block.get("channels") or [])
        if isinstance(ch, dict) and ch.get("url")
    ]
    if not declared:
        return [f"{environment}: no declared channels in pixi.lock"]

    platforms = platforms or list((env_block.get("packages") or {}).keys())
    findings: list[str] = []

    for plat_key in platforms:
        entries = (env_block.get("packages") or {}).get(plat_key) or []
        for entry in entries:
            if "conda" in entry:
                url = entry["conda"]
                if not any(url.startswith(f"{base}/") for base in declared):
                    findings.append(
                        f"channel audit ({plat_key}): conda package off declared "
                        f"channels: {url}"
                    )
            elif "conda_source" in entry:
                # Workspace path pins (``name @ src/...``) — not a remote channel fetch.
                continue
            elif "pypi" in entry:
                wheel_url = entry["pypi"]
                wheel_name = Path(urlparse(wheel_url).path).name.split("-")[0]
                if wheel_name not in PYPI_WHEEL_ALLOWLIST:
                    findings.append(
                        f"channel audit ({plat_key}): PyPI-only lock entry "
                        f"{wheel_name!r} is not on the SBOM PyPI allowlist "
                        f"(declared channels: conda-forge + SelfExplainML only)"
                    )
            else:
                kinds = ", ".join(sorted(entry))
                findings.append(
                    f"channel audit ({plat_key}): unknown lock entry kind(s): {kinds}"
                )
    return findings


def _run_import_probe(probe: str) -> None:
    subprocess.run(
        [sys.executable, "-c", probe],
        check=True,
        capture_output=True,
        text=True,
    )


def import_gap_findings(*, exclude_packages: frozenset[str] = frozenset()) -> list[str]:
    """Name packages a station import needs that are absent from the SBOM env."""
    gaps: list[str] = []
    for dist_name, probe in STATION_IMPORT_PROBES:
        if dist_name in exclude_packages:
            gaps.append(
                f"SBOM gap: {dist_name} (station import {probe!r} would fail)"
            )
            continue
        try:
            _run_import_probe(probe)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip().splitlines()
            tail = detail[-1] if detail else "import failed"
            gaps.append(f"SBOM gap: {dist_name} ({tail})")
    return gaps


def gather_findings(
    lockfile: dict,
    *,
    exclude_packages: frozenset[str] = frozenset(),
    platforms: list[str] | None = None,
) -> list[str]:
    out: list[str] = []
    if msg := assert_sbom_environment():
        out.append(msg)
    out.extend(channel_audit_findings(lockfile, platforms=platforms))
    out.extend(import_gap_findings(exclude_packages=exclude_packages))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Laptop SBOM gate (Story 67.2).")
    parser.add_argument(
        "--lockfile",
        type=Path,
        default=REPO_ROOT / "pixi.lock",
        help="pixi.lock to audit (default: repo root)",
    )
    parser.add_argument(
        "--exclude-package",
        action="append",
        default=[],
        metavar="DIST",
        help="Treat a distribution as missing (tests / gap simulation).",
    )
    parser.add_argument(
        "--platform",
        action="append",
        default=[],
        help="Limit channel audit to these pixi.lock platform keys.",
    )
    args = parser.parse_args(argv)

    if not args.lockfile.is_file():
        print(f"could not read lockfile: {args.lockfile}", file=sys.stderr)
        return 2

    try:
        import yaml
    except ImportError:
        print("PyYAML is required to parse pixi.lock", file=sys.stderr)
        return 2

    try:
        lockfile = yaml.safe_load(args.lockfile.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"could not parse lockfile: {exc}", file=sys.stderr)
        return 2

    if not isinstance(lockfile, dict):
        print("lockfile root is not a mapping", file=sys.stderr)
        return 2

    platforms = args.platform or None
    if platforms is None and not args.platform:
        platforms = _lock_platforms()
        # Map host platform to lock keys (osx-arm64-min in lock).
        env_pkgs = (lockfile.get("environments") or {}).get(SBOM_ENV, {}).get(
            "packages"
        ) or {}
        platforms = [p for p in platforms if p in env_pkgs] or list(env_pkgs.keys())

    exclude = frozenset(args.exclude_package)
    findings = gather_findings(
        lockfile, exclude_packages=exclude, platforms=platforms
    )
    for line in findings:
        print(line, file=sys.stderr)
    if findings:
        print(f"\nFINDINGS ({len(findings)}): laptop SBOM gate failed.", file=sys.stderr)
        return 1
    print("OK: laptop SBOM gate (channel audit + import probes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
