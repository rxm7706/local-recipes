"""Dogfood gate proof (Story 5.2, epics.md AC3):

(a) Warden scanning its OWN package (a staged copy of ``pyproject.toml`` +
``src/`` -- see ``scripts/dogfood_scan.py``'s module docstring for why the
real, un-staged package directory can't be scanned directly, and
``.warden-baseline.yaml``'s own header for why a handful of currently
unavoidable findings are grandfathered there) exits 0 on the real,
known-clean-modulo-committed-baseline state.
(b) The SAME staged setup, with one seeded, genuinely NEW compliance
violation added, exits non-zero -- proving the baseline can't blanket-
suppress a future regression it was never told about.

``scripts/dogfood_scan.py`` is loaded via ``importlib`` (mirrors
``tests/unit/test_refresh_kev_feed.py``'s own pattern) since ``scripts/``
sits outside the installed package.

Deviation from the spec's original "seed one unused dependency" wording
(recorded in this story's Design Notes): DEP002 (declared-but-unused) is
WARN-tier by this codebase's own DEFAULT hygiene policy (exit 0 --
extensively pinned elsewhere, e.g. ``test_scan_harness.py``'s
``test_deptry_unused_dependency_is_a_warning``), so seeding one would NOT
flip the exit code. DEP001 (imported-but-undeclared) is policy-violation by
the SAME default policy (exit 1) and achieves the identical observable
proof the spec intends: one seeded compliance problem makes an otherwise-
passing gate fail."""

from __future__ import annotations

import importlib.util
import json
from importlib import resources
from pathlib import Path

import jsonschema

from pyforge.warden.cli import main

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load_dogfood_scan():
    module_path = _SCRIPTS_DIR / "dogfood_scan.py"
    spec = importlib.util.spec_from_file_location("dogfood_scan", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_dogfood_scan = _load_dogfood_scan()
BASELINE_PATH = _dogfood_scan.BASELINE_PATH
stage_dogfood_copy = _dogfood_scan.stage_dogfood_copy


def load_schema() -> dict:
    schema_file = resources.files("pyforge.warden") / "data" / "report-schema.json"
    return json.loads(schema_file.read_text(encoding="utf-8"))


def parse_report(stdout: str) -> dict:
    document = json.loads(stdout)
    jsonschema.Draft202012Validator(load_schema()).validate(document)
    return document


def test_baseline_file_is_committed_and_provisioned():
    assert BASELINE_PATH.is_file(), (
        f"{BASELINE_PATH} missing -- the dogfood gate's committed "
        "grandfathering file"
    )


def test_dogfood_scan_of_the_real_package_exits_zero(tmp_path, capsys):
    dest = tmp_path / "pyforge-warden"
    stage_dogfood_copy(dest)
    capsys.readouterr()
    rc = main(
        ["scan", str(dest), "--format", "json", "--baseline", str(BASELINE_PATH)]
    )
    captured = capsys.readouterr()
    document = parse_report(captured.out)
    assert rc == 0
    assert rc == document["exit_code"]
    assert document["errors"] == []


def test_dogfood_seeded_violation_exits_nonzero(tmp_path, capsys):
    dest = tmp_path / "pyforge-warden-seeded"
    stage_dogfood_copy(dest)
    seed_name = "totally_undeclared_seeded_violation_pkg_xyz"
    (dest / "src" / "pyforge" / "warden" / "_seeded_dogfood_violation.py").write_text(
        f"import {seed_name}  # noqa: F401\n", encoding="utf-8"
    )
    capsys.readouterr()
    rc = main(
        ["scan", str(dest), "--format", "json", "--baseline", str(BASELINE_PATH)]
    )
    captured = capsys.readouterr()
    document = parse_report(captured.out)
    assert rc != 0
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "policy-violation"
    hygiene_ids = {
        f["id"] for f in document["findings"] if f["axis"] == "hygiene"
    }
    assert f"hygiene:DEP001:{seed_name}" in hygiene_ids
