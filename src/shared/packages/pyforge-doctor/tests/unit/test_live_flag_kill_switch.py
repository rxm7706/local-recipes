"""Story 58.2 (spec-pyforge-doctor:CAP-97) -- the live-tree half of ``test_flag_kill_switch.py``.

Two tests reach outside this package: the CLI kill switch resolves the tree through django-pyforge's
``django_pyforge.flags`` (its ``src`` on the import path), and the dated-flag case copies the shipped platform flag
tree. Every test that writes its own tree stays in the package half (``test_flag_kill_switch.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor.actuators.flag_kill_switch import disable_flag

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _sample_tree() -> dict:
    """The one-flag tree test_flag_kill_switch.py's package-half tests write (kept here, not imported from a test
    module)."""
    return {
        "flags": {
            "pyforge.three_surfaces": {
                "state": "ENABLED",
                "variants": {"on": True, "off": False},
                "defaultVariant": "on",
            }
        }
    }


def test_cli_kill_switch_edits_the_tree_itself_not_a_rendered_copy(tmp_path: Path, monkeypatch, capsys):
    """Story 76.1: with no ``--flags-path`` the actuator resolves the tree through
    ``django_pyforge.flags.resolve_tree_path``. ``resolve_flags_path`` now returns the
    per-environment rendering (a temp copy) whenever ``flag-overlays.json`` sits beside the
    tree, and a kill switch that edited the copy would report success and change nothing."""
    from pyforge.doctor.__main__ import main

    django_pyforge_src = Path(__file__).resolve().parents[3] / "django-pyforge" / "src"
    monkeypatch.syspath_prepend(str(django_pyforge_src))  # django_pyforge.flags imports no Django at module top
    tree = tmp_path / "flags.json"
    tree.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    (tmp_path / "flag-overlays.json").write_text(
        json.dumps({env: {"pyforge.three_surfaces": "on"} for env in ("dev", "staging", "production")}),
        encoding="utf-8",
    )
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.delenv("FLAGD_OFFLINE_FLAG_SOURCE_PATH", raising=False)
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)

    rc = main(["flags", "kill-switch", "--flag", "pyforge.three_surfaces", "--reason", "test"])

    assert rc == 0
    assert json.loads(tree.read_text(encoding="utf-8"))["flags"]["pyforge.three_surfaces"]["state"] == "DISABLED"
    assert str(tree) in capsys.readouterr().out
    # the overlay is a value document: the actuator leaves it alone
    assert json.loads((tmp_path / "flag-overlays.json").read_text(encoding="utf-8"))["production"] == {
        "pyforge.three_surfaces": "on"
    }


_DATED_KILL_FIXTURE = "pyforge.test.dated_kill_fixture"


def test_killing_a_dated_on_everywhere_flag_on_a_shipped_copy_leaves_the_tree_composable(tmp_path: Path, monkeypatch):
    """Story 76.2: ``disable_flag`` sets only ``state``. A flag with ``on_everywhere`` set
    must still compose after kill (Story 76.4 removed ``pyforge.three_surfaces`` from the
    shipped tree, so this copies the live tree and adds a dated fixture key)."""
    from pyforge.core import flags

    shipped_config = Path(__file__).resolve().parents[6] / "src" / "platform" / "config"
    tree = tmp_path / "flags.json"
    for name in ("flags.json", flags.OVERLAYS_FILE_NAME):
        source = shipped_config / name
        # The live half runs only where the tree exists: an absent shipped file is a failure, never a silent skip.
        assert source.is_file(), f"{source} is missing: the live-tree half copies the shipped platform flag tree"
        (tmp_path / name).write_bytes(source.read_bytes())

    payload = json.loads(tree.read_text(encoding="utf-8"))
    payload["flags"][_DATED_KILL_FIXTURE] = {
        "state": "ENABLED",
        "variants": {"on": True, "off": False},
        "defaultVariant": "on",
        "metadata": {
            "owner": "steward",
            "story": "76-4-fixture",
            "created": "2026-08-25",
            "on_everywhere": "2026-08-25",
            "cleanup_by": "2026-11-23",
        },
    }
    tree.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    disable_flag(tree, _DATED_KILL_FIXTURE)

    killed = json.loads(tree.read_text(encoding="utf-8"))["flags"][_DATED_KILL_FIXTURE]
    assert killed["state"] == "DISABLED"
    assert killed["metadata"]["on_everywhere"] == "2026-08-25"  # the clock is left as it was
    for environment in flags.ENVIRONMENTS:
        monkeypatch.setenv(flags.ENV_ENVIRONMENT, environment)
        assert flags.read_boolean(_DATED_KILL_FIXTURE, True, flags_path=tree) is False, environment
        assert flags.read_boolean("pyforge.steward.ghe_fleet_credentials", flags_path=tree) is False, environment
