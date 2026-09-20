"""Story 14.4 — CAP-4: pin fan-out enumerated, not discovered by red tests."""

from __future__ import annotations

import hashlib
import json
import textwrap
from pathlib import Path

from pyforge.steward.cli import EXIT_OK, main
from pyforge.steward.upgrade import (
    KNOWN_PIN_SITES,
    TRAP_PIN_FANOUT,
    build_pin_fan_out_report,
    catalog_site_ids_for,
    format_pin_fan_out,
)

_TRAP5_BMAD_LOOP_STATIC = catalog_site_ids_for("bmad-loop")
_TRAP5_BMAD_METHOD_STATIC = catalog_site_ids_for("bmad-method")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_trap5_repo(
    root: Path,
    *,
    loop_from: str = "0.10.0",
    loop_to: str = "0.11.0",
    method_from: str = "6.10.0",
    method_to: str = "6.11.0",
    move_root_loop: bool = False,
    move_marshal: bool = True,
) -> Path:
    """Minimal trap-5 layout: root floor + marshal pin sites + seed + drift map."""
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")

    root_loop = f">={loop_to}" if move_root_loop else f">={loop_from}"
    root_method = f">={method_to}"
    (root / "pixi.toml").write_text(
        textwrap.dedent(
            f"""\
            [dependencies]
            bmad-loop = "{root_loop}"
            bmad-method = "{root_method}"
            """
        ),
        encoding="utf-8",
    )

    marshal = root / "src" / "shared" / "packages" / "pyforge-marshal"
    (marshal / "src" / "pyforge" / "marshal" / "adapters").mkdir(parents=True)
    (marshal / "src" / "pyforge" / "marshal" / "seed" / "templates").mkdir(parents=True)
    (marshal / "tests" / "unit").mkdir(parents=True)

    loop_pin = f">={loop_to},<0.12" if move_marshal else f">={loop_from},<0.11"
    (marshal / "pyproject.toml").write_text(
        textwrap.dedent(
            f"""\
            [project]
            name = "pyforge-marshal"
            version = "0.0.0"
            dependencies = [
                "bmad-loop{loop_pin}",
            ]
            """
        ),
        encoding="utf-8",
    )
    (marshal / "pixi.toml").write_text(
        textwrap.dedent(
            f"""\
            [package]
            name = "pyforge-marshal"
            version = "0.0.0"

            [package.run-dependencies]
            bmad-loop = "{loop_pin}"
            """
        ),
        encoding="utf-8",
    )
    (marshal / "src" / "pyforge" / "marshal" / "adapters" / "harness_bmadloop.py").write_text(
        f'HARNESS_VERSION_RANGE_TEXT = "{loop_pin}"\n',
        encoding="utf-8",
    )

    seed_loop = f">={loop_to}" if move_marshal else f">={loop_from}"
    (marshal / "src" / "pyforge" / "marshal" / "seed" / "templates" / "manifest.yaml").write_text(
        textwrap.dedent(
            f"""\
            artifacts:
              - id: bmad-loop
                class: referenced
                path: "n/a"
                pin: "{seed_loop}"
              - id: bmad-method
                class: referenced
                path: "n/a"
                pin: ">={method_to}"
            """
        ),
        encoding="utf-8",
    )
    (marshal / "tests" / "unit" / "test_seed_templates_manifest.py").write_text(
        textwrap.dedent(
            f"""\
            expected = {{
                "bmad-method": ">={method_to}",
                "bmad-loop": "{seed_loop}",
            }}
            """
        ),
        encoding="utf-8",
    )
    return root


def test_catalog_names_exact_trap5_static_sites():
    """Fixture-covered against the 2026-08-21 trap-5 site list (static rows)."""
    assert _TRAP5_BMAD_LOOP_STATIC == (
        "root-pixi-floor:bmad-loop",
        "marshal-pyproject:bmad-loop",
        "marshal-pixi:bmad-loop",
        "harness-version-range:bmad-loop",
        "seed-manifest:bmad-loop",
        "drift-test-map:bmad-loop",
    )
    assert _TRAP5_BMAD_METHOD_STATIC == (
        "root-pixi-floor:bmad-method",
        "seed-manifest:bmad-method",
        "drift-test-map:bmad-method",
    )
    # Every catalog row is either loop or method — no orphan packages.
    assert {s.package for s in KNOWN_PIN_SITES} == {"bmad-loop", "bmad-method"}


def test_report_enumerates_moved_and_not_moved(tmp_path: Path):
    repo = _write_trap5_repo(tmp_path / "repo", move_root_loop=False, move_marshal=True)
    loops = tmp_path / "loops"
    home = loops / "pyforge-steward"
    (home / ".bmad-loop").mkdir(parents=True)
    (home / ".bmad-loop" / "bmad_loop_hook.py").write_text("# stale fixture relay\n", encoding="utf-8")

    report = build_pin_fan_out_report(
        repo=repo,
        package="bmad-loop",
        from_version="0.10.0",
        to_version="0.11.0",
        loops_home=loops,
    )

    by_id = {s.site_id: s for s in report.sites}
    for site_id in _TRAP5_BMAD_LOOP_STATIC:
        assert site_id in by_id, f"missing catalog site {site_id}"

    assert by_id["root-pixi-floor:bmad-loop"].status == "not_moved"
    assert by_id["root-pixi-floor:bmad-loop"].foreign is False
    assert by_id["marshal-pyproject:bmad-loop"].status == "moved"
    assert by_id["marshal-pyproject:bmad-loop"].foreign is True
    assert by_id["marshal-pixi:bmad-loop"].status == "moved"
    assert by_id["harness-version-range:bmad-loop"].status == "moved"
    assert by_id["seed-manifest:bmad-loop"].status == "moved"
    assert by_id["drift-test-map:bmad-loop"].status == "moved"

    relay = by_id["loop-home-relay:pyforge-steward"]
    assert relay.foreign is True
    assert relay.status in {"not_moved", "unknown"}  # stale vs packaged, or unknown
    assert report.trap_id == TRAP_PIN_FANOUT


def test_report_never_edits_foreign_or_local_files(tmp_path: Path):
    repo = _write_trap5_repo(tmp_path / "repo", move_marshal=False)
    tracked = [
        repo / "pixi.toml",
        repo / "src/shared/packages/pyforge-marshal/pyproject.toml",
        repo / "src/shared/packages/pyforge-marshal/pixi.toml",
        repo / "src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py",
        repo / "src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml",
        repo / "src/shared/packages/pyforge-marshal/tests/unit/test_seed_templates_manifest.py",
    ]
    before = {str(p): _sha(p) for p in tracked}

    report = build_pin_fan_out_report(
        repo=repo,
        package="bmad-loop",
        from_version="0.10.0",
        to_version="0.11.0",
        loops_home=tmp_path / "empty-loops",
    )
    assert all(s.status == "not_moved" for s in report.sites if not s.site_id.startswith("loop-home"))
    assert all(
        s.foreign
        for s in report.sites
        if s.site_id.startswith("marshal") or "seed" in s.site_id or "drift" in s.site_id or "harness" in s.site_id
    )

    after = {str(p): _sha(p) for p in tracked}
    assert before == after


def test_bmad_method_package_sites(tmp_path: Path):
    repo = _write_trap5_repo(tmp_path / "repo")
    report = build_pin_fan_out_report(
        repo=repo,
        package="bmad-method",
        from_version="6.10.0",
        to_version="6.11.0",
        loops_home=tmp_path / "loops",
    )
    ids = {s.site_id for s in report.sites}
    for site_id in _TRAP5_BMAD_METHOD_STATIC:
        assert site_id in ids
    # No loop-home relays for bmad-method.
    assert not any(s.site_id.startswith("loop-home-relay:") for s in report.sites)
    assert all(s.status == "moved" for s in report.sites)


def test_cli_pin_fan_out_json(tmp_path: Path, capsys):
    repo = _write_trap5_repo(tmp_path / "repo", move_root_loop=True, move_marshal=True)
    code = main(
        [
            "upgrade",
            "pin-fan-out",
            "--package",
            "bmad-loop",
            "--from",
            "0.10.0",
            "--to",
            "0.11.0",
            "--repo-root",
            str(repo),
            "--loops-home",
            str(tmp_path / "loops"),
            "--json",
        ]
    )
    assert code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["package"] == "bmad-loop"
    assert payload["trap_id"] == TRAP_PIN_FANOUT
    site_ids = {s["site_id"] for s in payload["sites"]}
    assert set(_TRAP5_BMAD_LOOP_STATIC) <= site_ids


def test_format_mentions_foreign(tmp_path: Path):
    repo = _write_trap5_repo(tmp_path / "repo")
    report = build_pin_fan_out_report(
        repo=repo,
        package="bmad-loop",
        from_version="0.10.0",
        to_version="0.11.0",
        loops_home=tmp_path / "loops",
    )
    text = format_pin_fan_out(report, as_json=False)
    assert "CAP-4 report-only" in text
    assert "foreign" in text
    assert "root-pixi-floor:bmad-loop" in text
