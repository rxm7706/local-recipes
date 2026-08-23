#!/usr/bin/env python3
"""platform-ci-test-requirements-check — requirements/*.txt vs pixi platform-ci-test.

The Platform CI `test` job can install deps via the slim pixi env
`platform-ci-test` (default) or legacy `pip install -r requirements/local.txt`.
The pixi feature's `[feature.platform-ci-test.pypi-dependencies]` table must
stay byte-for-byte aligned with the merged requirements chain:

    local.txt -> production.txt -> base.txt

Findings:
  missing-in-pixi   package pinned in requirements but absent from pixi
  extra-in-pixi     package in pixi but not in the requirements chain
  version-mismatch  same name, different == pin
  extras-mismatch   same name/version, different [extras]

Reconciler: `pixi run -e local-recipes fix-platform-ci-test-requirements`
(this script's `--fix` mutator), then `pixi lock`.

Exit codes: 0 clean, 1 drift found, 2 missing input file.
"""
from __future__ import annotations

DETECTOR = {"scope": "repo"}

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_ROOT = REPO_ROOT / "src" / "platform" / "requirements"
LOCAL_FILE = REQUIREMENTS_ROOT / "local.txt"
BASE_FILE = REQUIREMENTS_ROOT / "base.txt"
PRODUCTION_FILE = REQUIREMENTS_ROOT / "production.txt"
MANIFEST = REPO_ROOT / "pixi.toml"
FEATURE = "platform-ci-test"
PYPI_DEPS_HEADER = "[feature.platform-ci-test.pypi-dependencies]"

REQ_LINE_RE = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[([^\]]+)\])?==([^\s]+)$"
)


@dataclass(frozen=True)
class Pin:
    name: str
    version: str
    extras: tuple[str, ...]

    @property
    def normalized_name(self) -> str:
        return self.name.lower().replace("_", "-")


def _parse_extras(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(sorted(x.strip() for x in raw.split(",") if x.strip()))


def _parse_requirements_file(path: Path, seen: set[Path] | None = None) -> dict[str, Pin]:
    """Merge pins from a requirements file and any `-r` includes (later wins)."""
    seen = seen or set()
    if path in seen:
        raise RuntimeError(f"requirements include cycle at {path}")
    seen.add(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    pins: dict[str, Pin] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("-r "):
            include = path.parent / line[3:].strip()
            pins.update(_parse_requirements_file(include, seen))
            continue
        match = REQ_LINE_RE.match(line)
        if not match:
            raise RuntimeError(f"unsupported requirements line in {path}: {raw_line!r}")
        name, extras_raw, version = match.groups()
        pin = Pin(name=name, version=version, extras=_parse_extras(extras_raw))
        pins[pin.normalized_name] = pin
    return pins


def _direct_pins_ordered(path: Path) -> list[Pin]:
    """Pins declared directly in one file (ignores `-r` includes)."""
    if not path.is_file():
        raise FileNotFoundError(path)
    pins: list[Pin] = []
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-r "):
            continue
        match = REQ_LINE_RE.match(line)
        if not match:
            raise RuntimeError(f"unsupported requirements line in {path}: {raw_line!r}")
        name, extras_raw, version = match.groups()
        pin = Pin(name=name, version=version, extras=_parse_extras(extras_raw))
        if pin.normalized_name in seen:
            continue
        seen.add(pin.normalized_name)
        pins.append(pin)
    return pins


def _parse_pixi_pins(manifest: dict) -> dict[str, Pin]:
    feature = manifest.get("feature", {}).get(FEATURE, {})
    pypi = feature.get("pypi-dependencies") or {}
    pins: dict[str, Pin] = {}
    for name, spec in pypi.items():
        if isinstance(spec, dict):
            version = str(spec.get("version", "")).removeprefix("==")
            extras = tuple(sorted(spec.get("extras") or ()))
        else:
            version = str(spec).removeprefix("==")
            extras = ()
        pin = Pin(name=name, version=version, extras=extras)
        pins[pin.normalized_name] = pin
    return pins


def _pin_layer(normalized_name: str, *, local_keys: set[str], prod_keys: set[str]) -> str:
    if normalized_name in local_keys:
        return "local"
    if normalized_name in prod_keys:
        return "production"
    return "base"


def _pixi_toml_name(pin: Pin) -> str:
    return pin.name.lower().replace("_", "-")


def _format_pin_line(pin: Pin) -> str:
    name = _pixi_toml_name(pin)
    if pin.extras:
        extras = ", ".join(f'"{item}"' for item in pin.extras)
        return f'{name} = {{ version = "=={pin.version}", extras = [{extras}] }}'
    return f'{name} = "=={pin.version}"'


def _render_pypi_deps_block(merged: dict[str, Pin]) -> str:
    local_keys = {pin.normalized_name for pin in _direct_pins_ordered(LOCAL_FILE)}
    prod_keys = {pin.normalized_name for pin in _direct_pins_ordered(PRODUCTION_FILE)}
    sections = [
        ("base", "# base.txt", _direct_pins_ordered(BASE_FILE)),
        ("production", "# production.txt (on top of base)", _direct_pins_ordered(PRODUCTION_FILE)),
        ("local", "# local.txt (on top of production)", _direct_pins_ordered(LOCAL_FILE)),
    ]

    lines = [PYPI_DEPS_HEADER]
    emitted: set[str] = set()
    for layer_name, comment, ordered in sections:
        section_pins: list[Pin] = []
        for pin in ordered:
            key = pin.normalized_name
            if key in emitted or key not in merged:
                continue
            if _pin_layer(key, local_keys=local_keys, prod_keys=prod_keys) != layer_name:
                continue
            section_pins.append(merged[key])
            emitted.add(key)
        if not section_pins:
            continue
        lines.append(comment)
        lines.extend(_format_pin_line(merged[pin.normalized_name]) for pin in section_pins)

    for key in sorted(merged):
        if key in emitted:
            continue
        lines.append("# (requirements chain)")
        lines.append(_format_pin_line(merged[key]))
        emitted.add(key)

    return "\n".join(lines) + "\n"


def fix_manifest() -> bool:
    merged = _parse_requirements_file(LOCAL_FILE)
    text = MANIFEST.read_text(encoding="utf-8")
    if PYPI_DEPS_HEADER not in text:
        raise RuntimeError(f"{MANIFEST}: missing {PYPI_DEPS_HEADER}")
    start = text.index(PYPI_DEPS_HEADER)
    rest = text[start + len(PYPI_DEPS_HEADER) :]
    end_match = re.search(r"\n(?=\[feature\.|# --- pyforge-mason)", rest)
    end = start + len(PYPI_DEPS_HEADER) + (end_match.start() if end_match else len(rest))
    new_block = _render_pypi_deps_block(merged)
    new_text = text[:start] + new_block + text[end:]
    if new_text == text:
        return False
    MANIFEST.write_text(new_text, encoding="utf-8")
    return True


def run() -> tuple[list[dict], dict]:
    if not LOCAL_FILE.is_file():
        raise FileNotFoundError(LOCAL_FILE)
    if not MANIFEST.is_file():
        raise FileNotFoundError(MANIFEST)

    req_pins = _parse_requirements_file(LOCAL_FILE)
    pixi_pins = _parse_pixi_pins(tomllib.loads(MANIFEST.read_text(encoding="utf-8")))

    findings: list[dict] = []
    for key, req in sorted(req_pins.items()):
        pixi = pixi_pins.get(key)
        if pixi is None:
            findings.append(
                {
                    "kind": "missing-in-pixi",
                    "package": req.name,
                    "detail": f"requirements pin {req.name}=={req.version} "
                    f"has no [feature.{FEATURE}.pypi-dependencies] entry",
                }
            )
            continue
        if req.version != pixi.version:
            findings.append(
                {
                    "kind": "version-mismatch",
                    "package": req.name,
                    "detail": f"requirements=={req.version}, "
                    f"pixi=={pixi.version}",
                }
            )
        if req.extras != pixi.extras:
            findings.append(
                {
                    "kind": "extras-mismatch",
                    "package": req.name,
                    "detail": f"requirements extras {list(req.extras)!r}, "
                    f"pixi extras {list(pixi.extras)!r}",
                }
            )

    for key, pixi in sorted(pixi_pins.items()):
        if key not in req_pins:
            findings.append(
                {
                    "kind": "extra-in-pixi",
                    "package": pixi.name,
                    "detail": f"[feature.{FEATURE}.pypi-dependencies] entry "
                    f"{pixi.name}=={pixi.version} not in requirements chain",
                }
            )

    return findings, {
        "requirements_pins": len(req_pins),
        "pixi_pins": len(pixi_pins),
        "requirements_root": _display_path(LOCAL_FILE),
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="platform-ci-test-requirements-check",
        description="Detect drift between requirements/*.txt and platform-ci-test pixi pins.",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite [feature.platform-ci-test.pypi-dependencies] from requirements, "
        "then re-run the check (mutator — not run from detectors-ci)",
    )
    args = parser.parse_args()

    if args.fix:
        try:
            changed = fix_manifest()
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"platform-ci-test-requirements-check: {exc}", file=sys.stderr)
            return 2
        if changed:
            print(f"platform-ci-test-requirements-check: rewrote {PYPI_DEPS_HEADER} in pixi.toml")
        else:
            print(f"platform-ci-test-requirements-check: {PYPI_DEPS_HEADER} already matched requirements")

    try:
        findings, stats = run()
    except FileNotFoundError as exc:
        print(f"platform-ci-test-requirements-check: missing {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"platform-ci-test-requirements-check: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"findings": findings, **stats}, indent=2))
    else:
        print(
            "platform-ci-test-requirements-check: "
            f"{stats['requirements_pins']} requirements pin(s), "
            f"{stats['pixi_pins']} pixi pin(s)"
        )
        for item in findings:
            print(f"  [{item['kind']}] {item['package']}: {item['detail']}")

    if findings:
        if not args.fix:
            print(
                f"\nDRIFT: {len(findings)} finding(s). "
                f"Reconciler: pixi run -e local-recipes fix-platform-ci-test-requirements "
                f"(or edit pixi.toml to match {stats['requirements_root']}).",
                file=sys.stderr,
            )
        else:
            print(
                f"\nDRIFT: {len(findings)} finding(s) remain after --fix.",
                file=sys.stderr,
            )
        return 1
    print("  clean — requirements chain matches platform-ci-test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
