"""Story 53.1 (spec-pyforge-herald CAP-63): ``pyforge.herald.site_shell`` in both states.

The flag reaches the Pages build as ``PYFORGE_SITE_SHELL``, exported by ``python -m pyforge.herald.pages_env`` from the
flag tree; ``docs-site/src/lib/flags.ts`` reads it, and the theme rule, the header and the closed sidebar groups follow
it. The model runs through node with type stripping (no ``node_modules``); the built pages are
``tests/meta/test_site_shell.py``'s (flag on) and ``tests/meta/test_one_generator.py``'s (flag off).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.herald import pages_env
from pyforge.herald.site_shell import SITE_SHELL_FLAG, site_shell_enabled

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "meta"))
from pages_astro import DOCS_SITE, needs_node, ts  # noqa: E402 -- the shared Pages helpers

# This module reads the live tree outside its package (docs-site/), so it runs in herald's live-tree half.
pytestmark = pytest.mark.live_tree

_FLAG = "pyforge.herald.site_shell"
flag_provider = make_flag_provider_fixture()

FLAGS_TS = DOCS_SITE / "src" / "lib" / "flags.ts"
SITE_HEADER_TS = DOCS_SITE / "src" / "lib" / "site-header.ts"
NAV_TS = DOCS_SITE / "src" / "lib" / "nav.ts"


def test_the_flag_key_is_the_one_the_tree_registers() -> None:
    assert SITE_SHELL_FLAG == _FLAG


@needs_node
@flag_states("pyforge.herald.site_shell")
def test_the_build_env_the_theme_rule_and_the_sidebar_follow_the_flag_state(
    flag_provider: dict[str, bool], tmp_path: Path
) -> None:
    """Two states: the Guild step's export says the flag's state, the docs-site reads that variable as the flag, and
    with it on a reader who stored no theme gets dark and the sidebar's groups start closed; off, the system scheme
    decides and the groups start open, as before the story."""
    enabled = flag_provider[_FLAG]
    tree = flagd_tree(tmp_path, {_FLAG: "on" if enabled else "off"})
    assert site_shell_enabled(flags_path=tree) is enabled
    env = pages_env.build_env(flags_path=tree)
    assert env["PYFORGE_SITE_SHELL"] == ("1" if enabled else "0")
    assert ts(FLAGS_TS, "return m.envFlagOn('PYFORGE_SITE_SHELL', inp.env);", env=env) is enabled
    script = ts(SITE_HEADER_TS, "return m.themeScript(inp.on);", on=enabled)
    assert isinstance(script, str)
    assert ("(s()||'dark')" in script) is enabled
    assert ("m.matches?'light':'dark'" in script) is not enabled
    groups = ts(
        NAV_TS,
        "const sections = [{key: 'herald', label: 'Herald', href: 'herald/', owner: 'herald', order: 10,"
        " entries: [{key: 'overview', label: 'Overview', href: 'herald/'}]}];"
        "return m.sectionGroups(sections, inp.on);",
        on=enabled,
    )
    assert isinstance(groups, list) and groups[0]["collapsed"] is enabled
