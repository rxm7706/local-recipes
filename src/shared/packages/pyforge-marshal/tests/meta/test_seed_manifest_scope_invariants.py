"""Story 97.2 AC1: adopt and update share one manifest scoping function."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pytest

from pyforge.marshal.seed.model.manifest import load_manifest, manifest_for_adopt_scope


def test_adopt_and_update_modules_do_not_define_private_manifest_filters():
    adopt_src = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal" / "seed" / "verbs" / "adopt.py"
    update_src = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal" / "seed" / "verbs" / "update.py"
    for path in (adopt_src, update_src):
        text = path.read_text(encoding="utf-8")
        assert "def _manifest_for_" not in text, f"{path.name} must not define a private manifest filter"


@pytest.mark.parametrize("slug,in_loop_home", [(None, None), ("demo", False), ("demo", True)])
def test_manifest_for_adopt_scope_renders_slug_and_respects_loop_home(slug, in_loop_home):
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        manifest = load_manifest(manifest_path)
    scoped = manifest_for_adopt_scope(manifest, slug, in_loop_home=in_loop_home)
    paths = {entry.path for entry in scoped.entries}
    assert "{{" not in "".join(paths)
    if in_loop_home is False:
        assert ".bmad-loop/policy.toml" not in paths
