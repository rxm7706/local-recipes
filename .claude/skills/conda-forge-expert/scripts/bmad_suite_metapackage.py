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


def _version_max(a: str, b: str) -> str:
    if PkgVersion is not None:
        try:
            return str(max(PkgVersion(a), PkgVersion(b)))
        except Exception:
            pass
    return a if a >= b else b


def _load_journal_moves(journal_path: Path) -> dict[str, str]:
    """Highest ``to`` per package where ``from`` != ``to`` (estate refresh journal)."""
    raw = json.loads(journal_path.read_text(encoding="utf-8"))
    best: dict[str, str] = {}
    for entry in raw.get("moves") or []:
        if not isinstance(entry, dict):
            continue
        pkg = str(entry.get("package") or "").strip()
        if not pkg:
            continue
        fr = entry.get("from")
        to = entry.get("to")
        if fr is None or to is None or str(fr) == str(to):
            continue
        moved_to = str(to).strip()
        prev = best.get(pkg)
        if prev is None:
            best[pkg] = moved_to
        else:
            best[pkg] = _version_max(moved_to, prev)
    return best


def _batch_floor(
    *,
    recipe_version: str,
    suite_floor: str | None,
    moved_to: str | None,
) -> tuple[str, str]:
    if moved_to is not None:
        floor = _version_max(moved_to, suite_floor) if suite_floor is not None else moved_to
        return floor, "batch-move"
    if suite_floor is None:
        return recipe_version, "member-recipe"
    if PkgVersion is not None:
        try:
            if PkgVersion(suite_floor) >= PkgVersion(recipe_version):
                return suite_floor, "suite-floor"
        except Exception:
            pass
    elif suite_floor >= recipe_version:
        return suite_floor, "suite-floor"
    return recipe_version, "member-recipe"


def _fallback_from_source(source: str, registry: str, *, offline: bool) -> bool:
    if offline:
        return False
    if source in ("recipe-floor", "npm-fallback", "github-fallback"):
        return True
    return registry == "pypi" and source == "npm"


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
) -> tuple[str, str, bool]:
    registry = _member_registry(recipe)
    upstream_name = _member_upstream_name(recipe, package)
    floor = _member_floor(recipe)

    if offline:
        return floor, "offline", False

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
    fallback = _fallback_from_source(source, registry, offline=offline)
    return final, source, fallback


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
    journal: Path | None = None,
    as_json: bool = False,
) -> tuple[list[MemberPin], list[ManifestMember], dict[str, Any] | None]:
    members = _load_manifest(root)
    deprecated = [m for m in members if m.deprecated]
    batch_moves = _load_journal_moves(journal) if journal is not None else {}

    recipe_path = root / "recipes" / "bmad-suite" / "recipe.yaml"
    old_text = recipe_path.read_text(encoding="utf-8")
    old_pins = _parse_existing_pins(old_text)
    version_before = re.search(r'version:\s*"([^"]+)"', old_text).group(1)  # type: ignore[union-attr]

    pins: list[MemberPin] = []
    member_rows: list[dict[str, Any]] = []
    for member in members:
        if member.deprecated:
            continue
        name = member.name
        recipe = _read_member_recipe(root, name)
        recipe_version = _member_floor(recipe)
        registry = _member_registry(recipe)
        floor_before = old_pins.get(name)
        moved_to = batch_moves.get(name) if journal is not None else None
        fallback = False
        if journal is not None:
            floor, source = _batch_floor(
                recipe_version=recipe_version,
                suite_floor=floor_before,
                moved_to=moved_to,
            )
        else:
            floor, source, fallback = _resolve_upstream(name, recipe, offline=offline)
        pins.append(
            MemberPin(
                name=name,
                floor=floor,
                registry=registry,
                upstream=floor if source not in ("recipe-floor", "offline") else None,
                source=source,
                description=member.description,
                urls=member.urls,
            )
        )
        if as_json:
            member_rows.append(
                {
                    "name": name,
                    "registry": registry,
                    "recipe_version": recipe_version,
                    "moved_to": moved_to,
                    "floor_before": floor_before,
                    "floor": floor,
                    "source": source,
                    "fallback": fallback,
                }
            )

    new_pin_map = {p.name: p.floor for p in pins}
    bump_version = new_pin_map != old_pins
    version = _calver_stamp() if bump_version else version_before

    run_lines = _format_run_lines(pins)
    before, after = _rewrite_recipe(recipe_path, run_lines=run_lines, version=version)
    written = not dry_run and after != before
    if written:
        recipe_path.write_text(after, encoding="utf-8")

    report: dict[str, Any] | None = None
    if as_json:
        report = {
            "version_before": version_before,
            "version": version,
            "written": written,
            "members": member_rows,
        }
        print(json.dumps(report, indent=2))
    else:
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
        elif written:
            print(f"\nWrote {recipe_path}")
        else:
            print("\nNo changes.")
    return pins, deprecated, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate recipes/bmad-suite/recipe.yaml pins.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Repo root (auto-detected)")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use each member recipe's context.version (no network)",
    )
    parser.add_argument(
        "--journal",
        type=Path,
        default=None,
        help="Estate refresh journal: batch mode (no upstream lookups)",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable report")
    args = parser.parse_args()
    root = _repo_root(args.repo_root)
    if args.journal is not None and args.offline:
        raise SystemExit("--journal and --offline are mutually exclusive")
    generate(
        root,
        dry_run=args.dry_run,
        offline=args.offline,
        journal=args.journal,
        as_json=args.as_json,
    )


if __name__ == "__main__":
    main()
