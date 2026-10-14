"""Story 30.3 (fix under spec-pyforge-herald CAP-55 / Story 30.1): every React deck's lock resolves its manifest.

Story 30.1 (``697c985d25``) added ``@fontsource/archivo-expanded`` -- a package npm does not publish -- to
thirteen decks' ``package.json`` and never regenerated a ``package-lock.json`` in any of the fourteen, so
``npm ci`` and ``npm run build`` failed in every deck and herald's ``deck pull`` prover
(``deck_pipeline.NpmLocalProver``) could never pass. This meta-test reads the live tree offline, stdlib only:
a deck whose lock lacks a ``node_modules/<name>`` entry for a declared dependency, or whose lock root
(``packages[""]``) disagrees with ``package.json``, fails its own parametrised case.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[6]
_DECK_PACKAGE_FILES = sorted((_REPO_ROOT / "presentations").glob("*/package.json"))
_SECTIONS = ("dependencies", "devDependencies")


def lockfile_findings(deck_dir: Path) -> list[str]:
    """Every way ``deck_dir``'s ``package-lock.json`` fails to resolve its ``package.json``, one line each."""
    package = json.loads((deck_dir / "package.json").read_text(encoding="utf-8"))
    lock_path = deck_dir / "package-lock.json"
    if not lock_path.is_file():
        return [f"{deck_dir.name}: no package-lock.json beside package.json"]
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        return [
            f"{deck_dir.name}: package-lock.json has no `packages` map (lockfileVersion {lock.get('lockfileVersion')!r})"
        ]
    findings: list[str] = []
    for section in _SECTIONS:
        for name in package.get(section, {}):
            if f"node_modules/{name}" not in packages:
                findings.append(
                    f"{deck_dir.name}: {section} `{name}` has no node_modules/{name} entry in package-lock.json"
                )
    root = packages.get("", {})
    for section in _SECTIONS:
        declared = package.get(section, {})
        locked = root.get(section, {})
        if declared != locked:
            findings.append(
                f'{deck_dir.name}: package-lock.json packages[""].{section} is {locked!r}, package.json says {declared!r}'
            )
    return findings


def test_live_tree_has_react_decks():
    assert _DECK_PACKAGE_FILES, f"no presentations/*/package.json under {_REPO_ROOT}"


@pytest.mark.parametrize("package_file", _DECK_PACKAGE_FILES, ids=lambda p: p.parent.name)
def test_live_deck_lockfile_resolves_its_package_json(package_file: Path):
    findings = lockfile_findings(package_file.parent)
    assert not findings, "\n".join(findings)


def _write_deck(deck_dir: Path, package: dict, lock: dict | None) -> None:
    deck_dir.mkdir(parents=True)
    (deck_dir / "package.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    if lock is not None:
        (deck_dir / "package-lock.json").write_text(json.dumps(lock, indent=2), encoding="utf-8")


def _lock_for(package: dict, *entries: str) -> dict:
    root = {"name": package["name"], **{s: package[s] for s in _SECTIONS if s in package}}
    return {
        "name": package["name"],
        "lockfileVersion": 3,
        "packages": {"": root, **{f"node_modules/{e}": {"version": "0.0.0"} for e in entries}},
    }


def test_stale_lock_names_each_missing_dependency_and_the_root_mismatch(tmp_path: Path):
    # Story 30.1's shape: two font packages declared, the lock still from before they were added.
    before = {"name": "demo", "dependencies": {"react": "^18.3.1"}, "devDependencies": {"vite": "^5.4.11"}}
    after = {
        "name": "demo",
        "dependencies": {"react": "^18.3.1", "@fontsource/archivo": "^5.2.5", "@fontsource/phantom": "^5.2.5"},
        "devDependencies": {"vite": "^5.4.11"},
    }
    _write_deck(tmp_path / "demo", after, _lock_for(before, "react", "vite"))
    findings = lockfile_findings(tmp_path / "demo")
    assert [f.split(" has no ")[0] for f in findings if " has no " in f] == [
        "demo: dependencies `@fontsource/archivo`",
        "demo: dependencies `@fontsource/phantom`",
    ]
    assert [f for f in findings if 'packages[""].dependencies' in f]
    assert not [f for f in findings if 'packages[""].devDependencies' in f]


def test_missing_lock_is_one_finding(tmp_path: Path):
    _write_deck(tmp_path / "demo", {"name": "demo", "dependencies": {"react": "^18.3.1"}}, None)
    assert lockfile_findings(tmp_path / "demo") == ["demo: no package-lock.json beside package.json"]


def test_current_lock_has_no_finding(tmp_path: Path):
    package = {
        "name": "demo",
        "dependencies": {"react": "^18.3.1", "@fontsource-variable/archivo": "^5.2.5"},
        "devDependencies": {"vite": "^5.4.11"},
    }
    _write_deck(tmp_path / "demo", package, _lock_for(package, "react", "@fontsource-variable/archivo", "vite"))
    assert lockfile_findings(tmp_path / "demo") == []
