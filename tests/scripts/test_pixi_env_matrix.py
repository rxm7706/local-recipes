"""Unit tests for scripts/pixi_env_matrix.py (Story 43.5)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "pixi_env_matrix.py"


def _load():
    spec = importlib.util.spec_from_file_location("pixi_env_matrix_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pixi_env_matrix_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_build_rows_reads_python_platforms_and_counts(tmp_path: Path):
    mod = _load()
    lock = {
        "environments": {
            "alpha": {
                "packages": {
                    "linux-64": [
                        {"conda": "https://conda.anaconda.org/conda-forge/linux-64/python-3.14.7-hcd007b5_101_cp314.conda"},
                        {"conda": "https://conda.anaconda.org/conda-forge/linux-64/zlib-1.3.2-h25fd6f3_3.conda"},
                    ],
                    "win-64": [
                        {"conda": "https://conda.anaconda.org/conda-forge/win-64/python-3.14.7-h53f6dd8_101_cp314.conda"},
                    ],
                }
            },
            "beta": {
                "packages": {
                    "linux-64": [
                        {"conda": "https://conda.anaconda.org/conda-forge/linux-64/python-3.12.14-h8ab3286_0_cpython.conda"},
                    ]
                }
            },
        }
    }
    lock_path = tmp_path / "pixi.lock"
    lock_path.write_text(yaml.dump(lock), encoding="utf-8")

    rows = mod.build_rows(lock)
    by_name = {row.name: row for row in rows}
    assert by_name["alpha"].python == "3.14.*"
    assert by_name["alpha"].conda_records == 2
    assert by_name["alpha"].platforms == ("linux-64", "win-64")
    assert by_name["beta"].python == "3.12.*"
    assert by_name["beta"].conda_records == 1


def test_matrix_is_stale_when_lock_digest_changes(tmp_path: Path):
    mod = _load()
    lock_path = tmp_path / "pixi.lock"
    dream_path = tmp_path / "dream.md"
    lock_path.write_text("version: 1\n", encoding="utf-8")
    digest = mod.lock_digest(lock_path)
    dream_path.write_text(
        f"## Pixi environment matrix (measured)\n\n"
        f"{mod.BEGIN_MARKER} lock-sha256={digest} -->\n"
        f"| env | py |\n"
        f"{mod.END_MARKER}\n",
        encoding="utf-8",
    )
    assert mod.matrix_is_stale(dream_path, lock_path) is False

    lock_path.write_text("version: 2\n", encoding="utf-8")
    assert mod.matrix_is_stale(dream_path, lock_path) is True


def test_update_dream_inserts_measured_section(tmp_path: Path):
    mod = _load()
    lock = {
        "environments": {
            "demo": {
                "packages": {
                    "linux-64": [
                        {"conda": "https://conda.anaconda.org/conda-forge/linux-64/python-3.14.7-hcd007b5_101_cp314.conda"},
                    ]
                }
            }
        }
    }
    lock_path = tmp_path / "pixi.lock"
    lock_path.write_text(yaml.dump(lock), encoding="utf-8")
    dream_path = tmp_path / "dream.md"
    dream_path.write_text(
        "# Dream\n\n## Fleet conventions (one vocabulary)\n\nEvidence table.\n",
        encoding="utf-8",
    )

    updated = mod.update_dream(dream_path, lock_path)
    assert "## Pixi environment matrix (measured)" in updated
    assert mod.BEGIN_MARKER in updated
    assert "``demo``" in updated
    assert updated.index("## Pixi environment matrix (measured)") < updated.index(
        "## Fleet conventions (one vocabulary)"
    )
