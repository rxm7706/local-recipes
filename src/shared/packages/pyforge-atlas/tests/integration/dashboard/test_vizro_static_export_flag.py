"""Story 30.2 (CAP-63) AC9: the export in both states of ``pyforge.atlas.vizro_static_boards``.

``flag_states`` installs OpenFeature's in-memory provider, so this module needs ``openfeature``:
it runs in ``-e pyforge-atlas`` (``pyforge-atlas-test``) and is skipped in ``-e local-recipes``
(``dashboard-dryrun``), which does not carry it. The state drives the task through a flagd tree
written for it, the way Story 30.1's two-state test drives its manifest tool.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("openfeature")

from pyforge.testing_kit.flags import flag_states, flagd_tree  # noqa: E402

from .test_vizro_static_export import FIXTURE_ROOT, _page_ids, assert_export_shape, cli  # noqa: E402

_FLAG = "pyforge.atlas.vizro_static_boards"


@flag_states(_FLAG)
def test_ac9_the_export_in_both_flag_states(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    flag_on = flag_provider[_FLAG]
    tree = flagd_tree(tmp_path, {_FLAG: "on" if flag_on else "off"})
    out = tmp_path / "vizro"
    monkeypatch.setenv("GITHUB_SHA", "c" * 40)
    code = cli.main(["--out", str(out), "--flags-path", str(tree), "--data-root", FIXTURE_ROOT])
    if not flag_on:
        assert code == 2
        assert f"flag {_FLAG} is off" in capsys.readouterr().err
        assert not out.exists()
        return
    assert code == 0
    manifest = assert_export_shape(out, _page_ids())
    assert manifest["export_commit"] == "c" * 40
