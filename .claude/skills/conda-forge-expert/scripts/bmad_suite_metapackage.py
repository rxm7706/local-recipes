#!/usr/bin/env python3
"""
Regenerate ``recipes/bmad-suite/recipe.yaml`` run requirements from the suite
manifest and each member's ``cfe-upstream-registry``.

Resolves upstream latest per registry class (github / npm / pypi) — never
npm-first for GitHub-canonical packages. Rewrites the GENERATED block and bumps
the metapackage CalVer stamp when any pin changes.

Usage:
    python bmad_suite_metapackage.py
    python bmad_suite_metapackage.py --dry-run
    python bmad_suite_metapackage.py --repo-root /path/to/local-recipes
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required") from exc

try:
    from packaging.version import Version as PkgVersion
except ImportError:
    PkgVersion = None  # type: ignore[assignment,misc]

_SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from github_version_checker import get_latest_github_release  # type: ignore[import-not-found]
except ImportError:
    get_latest_github_release = None  # type: ignore[assignment,misc]

_GENERATED_BEGIN = "# GENERATED-BEGIN: suite-run-requirements"
_GENERATED_END = "# GENERATED-END: suite-run-requirements"
_FETCH_TIMEOUT = 15

# mybmad-dashboard skips win upstream — mirror install-matrix platform note.
_PLATFORM_SELECTORS: dict[str, str] = {
    "mybmad-dashboard": "linux or osx",
}


@dataclass(frozen=True)
class ManifestMember:
    name: str
    deprecated: bool = False
    notes: str = ""
    description: str = ""
    urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class MemberPin:
    name: str
    floor: str
    registry: str
    upstream: str | None
    source: str
    description: str = ""
    urls: tuple[str, ...] = ()


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "recipes" / "bmad-suite" / "suite-members.yaml").is_file():
            return parent
    raise SystemExit("Could not locate repo root (pass --repo-root)")


def _load_manifest(root: Path) -> list[ManifestMember]:
    manifest_path = root / "recipes" / "bmad-suite" / "suite-members.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    members = data.get("members") or []
    parsed: list[ManifestMember] = []
    for entry in members:
        if isinstance(entry, dict) and entry.get("name"):
            parsed.append(
                ManifestMember(
                    name=str(entry["name"]),
                    deprecated=bool(entry.get("deprecated")),
                    notes=str(entry.get("notes") or ""),
                    description=str(entry.get("description") or ""),
                    urls=tuple(str(u) for u in (entry.get("urls") or [])),
                )
            )
        elif isinstance(entry, str):
            parsed.append(ManifestMember(name=entry))
    if not parsed:
        raise SystemExit(f"No members in {manifest_path}")
    return parsed


def _read_member_recipe(root: Path, name: str) -> dict[str, Any]:
    path = root / "recipes" / name / "recipe.yaml"
    if not path.is_file():
        raise FileNotFoundError(path)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _member_floor(recipe: dict[str, Any]) -> str:
    context = recipe.get("context") or {}
    version = context.get("version")
    if version is None:
        raise ValueError("missing context.version")
    return str(version).strip().strip('"')


def _member_registry(recipe: dict[str, Any]) -> str:
    extra = recipe.get("extra") or {}
    reg = extra.get("cfe-upstream-registry")
    return str(reg).strip().lower() if reg else ""


def _member_upstream_name(recipe: dict[str, Any], package: str) -> str:
    extra = recipe.get("extra") or {}
    name = extra.get("cfe-upstream-name")
    return str(name).strip() if name else package


def _fetch_json(url: str) -> Any:
    with urlopen(url, timeout=_FETCH_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def _fetch_pypi_latest(package: str) -> str | None:
    try:
        body = _fetch_json(f"https://pypi.org/pypi/{package}/json")
        return str(body["info"]["version"])
    except (HTTPError, URLError, KeyError, TypeError, ValueError):
        return None


def _fetch_npm_latest(package: str) -> str | None:
    try:
        body = _fetch_json(f"https://registry.npmjs.org/{package}/latest")
        return str(body["version"])
    except (HTTPError, URLError, KeyError, TypeError, ValueError):
        return None


def _fetch_github_latest(owner_repo: str) -> str | None:
    if get_latest_github_release is None:
        return None
    if "/" not in owner_repo:
        return None
    owner, repo = owner_repo.split("/", 1)
    try:
        latest = get_latest_github_release(owner, repo)
        return str(latest["version"])
    except (RuntimeError, KeyError, TypeError):
        return None


def _prefer_floor(floor: str, candidate: str | None) -> tuple[str, str]:
    """Never pin below the member recipe's declared floor; prefer the higher release."""
    if candidate is None:
        return floor, "recipe-floor"
    if PkgVersion is not None:
        try:
            if PkgVersion(candidate) < PkgVersion(floor):
                return floor, "recipe-floor"
        except Exception:
            pass
    return candidate, "resolved"


def _resolve_upstream(
    package: str, recipe: dict[str, Any], *, offline: bool
) -> tuple[str, str]:
    registry = _member_registry(recipe)
    upstream_name = _member_upstream_name(recipe, package)
    floor = _member_floor(recipe)

    if offline:
        return floor, "offline"

    resolved: str | None = None
    source = "recipe-floor"

    if registry == "github":
        resolved = _fetch_github_latest(upstream_name)
        source = "github" if resolved else "recipe-floor"
    elif registry == "pypi":
        resolved = _fetch_pypi_latest(upstream_name)
        if resolved is None:
            resolved = _fetch_npm_latest(package)
            source = "npm" if resolved else "recipe-floor"
        else:
            source = "pypi"
    elif registry == "npm":
        resolved = _fetch_npm_latest(upstream_name)
        source = "npm" if resolved else "recipe-floor"
    else:
        resolved = _fetch_npm_latest(package)
        if resolved:
            source = "npm-fallback"
        else:
            resolved = _fetch_github_latest(upstream_name)
            source = "github-fallback" if resolved else "recipe-floor"

    final, src = _prefer_floor(floor, resolved)
    if final == floor and source != "recipe-floor":
        source = f"{source}+floor"
    elif final == floor:
        source = "recipe-floor"
    return final, source


def _calver_stamp(when: date | None = None) -> str:
    today = when or date.today()
    return f"{today.year}.{today.month}.{today.day}"


def _member_comment(pin: MemberPin) -> str:
    """The trailing `# <description> # <url> # <url>` for one member, or "".

    Sourced from suite-members.yaml so it survives regeneration — a comment
    hand-added to the GENERATED block is wiped on the next run.
    """
    parts = [pin.description.strip()] if pin.description.strip() else []
    parts.extend(u.strip() for u in pin.urls if u.strip())
    return "  # " + " # ".join(parts) if parts else ""


def _format_run_lines(pins: list[MemberPin]) -> list[str]:
    # Align every trailing comment to one column: the widest emitted dep line
    # plus a two-space gutter. Selector-nested members are indented deeper but
    # share the same absolute column, so the block reads as one table.
    rendered: list[tuple[str, MemberPin | None]] = []
    for pin in pins:
        selector = _PLATFORM_SELECTORS.get(pin.name)
        if selector:
            rendered.append((f"    - if: {selector}", None))
            rendered.append(("      then:", None))
            rendered.append((f"        - {pin.name} >={pin.floor}", pin))
        else:
            rendered.append((f"    - {pin.name} >={pin.floor}", pin))

    width = max(
        (len(text) for text, pin in rendered if pin is not None and _member_comment(pin)),
        default=0,
    )

    lines: list[str] = []
    for text, pin in rendered:
        comment = _member_comment(pin) if pin is not None else ""
        lines.append(f"{text.ljust(width)}{comment}" if comment else text)
    return lines


def _parse_existing_pins(text: str) -> dict[str, str]:
    inside = False
    pins: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if _GENERATED_BEGIN in raw:
            inside = True
            continue
        if _GENERATED_END in raw:
            break
        if not inside:
            continue
        m = re.match(r"-\s+([\w-]+)\s+>=(\s*)(\S+)", line)
        if m:
            pins[m.group(1)] = m.group(3)
    return pins


def _rewrite_recipe(
    recipe_path: Path,
    *,
    run_lines: list[str],
    version: str,
) -> tuple[str, str]:
    text = recipe_path.read_text(encoding="utf-8")
    block = "\n".join(
        [
            "  run:",
            *run_lines,
        ]
    )
    # Capture the BEGIN marker LINE only (`[^\n]*` keeps its trailing
    # "do not edit by hand" note); the old body is consumed by `.*?` and
    # dropped. Keeping `.*?` inside the group made `\1` re-emit the stale
    # block, so each run APPENDED a second `run:` key under `requirements:`
    # instead of replacing the first.
    pattern = re.compile(
        rf"({_re_escape(_GENERATED_BEGIN)}[^\n]*)\n.*?{_re_escape(_GENERATED_END)}",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"GENERATED markers not found in {recipe_path}")
    new_text = pattern.sub(
        rf"\1\n{block}\n  {_GENERATED_END.lstrip()}",
        text,
        count=1,
    )
    # `[^\S\n]` (blank-but-not-newline) rather than `\s`: a bare `\s*$` under
    # MULTILINE swallows the newline(s) AFTER the match, silently deleting the
    # blank line that separates `context:` from `package:`.
    ver_pattern = re.compile(
        r'(^[^\S\n]*version:[^\S\n]*")[\d.]+(")[^\S\n]*$',
        re.MULTILINE,
    )
    new_text, n = ver_pattern.subn(rf"\g<1>{version}\g<2>", new_text, count=1)
    if n != 1:
        raise SystemExit(f"Could not update context.version in {recipe_path}")
    return text, new_text


def _re_escape(text: str) -> str:
    return re.escape(text)


def generate(
    root: Path,
    *,
    dry_run: bool = False,
    offline: bool = False,
) -> tuple[list[MemberPin], list[ManifestMember]]:
    members = _load_manifest(root)
    deprecated = [m for m in members if m.deprecated]
    pins: list[MemberPin] = []
    for member in members:
        if member.deprecated:
            continue
        name = member.name
        recipe = _read_member_recipe(root, name)
        floor, source = _resolve_upstream(name, recipe, offline=offline)
        pins.append(
            MemberPin(
                name=name,
                floor=floor,
                registry=_member_registry(recipe),
                upstream=floor if source != "recipe-floor" else None,
                source=source,
                description=member.description,
                urls=member.urls,
            )
        )

    recipe_path = root / "recipes" / "bmad-suite" / "recipe.yaml"
    old_text = recipe_path.read_text(encoding="utf-8")
    old_pins = _parse_existing_pins(old_text)
    new_pin_map = {p.name: p.floor for p in pins}
    bump_version = new_pin_map != old_pins
    version = _calver_stamp() if bump_version else re.search(
        r'version:\s*"([^"]+)"', old_text
    ).group(1)  # type: ignore[union-attr]

    run_lines = _format_run_lines(pins)
    before, after = _rewrite_recipe(recipe_path, run_lines=run_lines, version=version)

    print("bmad-suite metapackage refresh")
    print("=" * 60)
    print("active (recipe.yaml run deps):")
    for pin in pins:
        old = old_pins.get(pin.name, "—")
        changed = " *" if old != pin.floor else ""
        print(
            f"  {pin.name:42} {old:>16} -> {pin.floor:<16} "
            f"[{pin.source}]{changed}"
        )
    if deprecated:
        print("\ndeprecated (manifest only — skipped in recipe.yaml):")
        for member in deprecated:
            note = f" — {member.notes}" if member.notes else ""
            print(f"  {member.name}{note}")
    print(f"\nmetapackage version: {version}")
    if dry_run:
        print("\n(dry-run — recipe.yaml not written)")
        return pins, deprecated
    if after != before:
        recipe_path.write_text(after, encoding="utf-8")
        print(f"\nWrote {recipe_path}")
    else:
        print("\nNo changes.")
    return pins, deprecated


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate recipes/bmad-suite/recipe.yaml pins.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Repo root (auto-detected)")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use each member recipe's context.version (no network)",
    )
    args = parser.parse_args()
    root = _repo_root(args.repo_root)
    pins, deprecated = generate(root, dry_run=args.dry_run, offline=args.offline)


if __name__ == "__main__":
    main()
