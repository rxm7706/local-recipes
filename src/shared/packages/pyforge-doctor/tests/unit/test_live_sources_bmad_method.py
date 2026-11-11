"""Story 58.2 (spec-pyforge-doctor:CAP-97) -- the live-tree half of ``test_sources_bmad_method.py``.

The GitHub fallback is proven here on the repository's own ``recipes/<name>/recipe.yaml`` (story 41.4, DW-FU-15-1-2);
every test that builds its own tree stays in the package half (``test_sources_bmad_method.py``). ``urlopen`` is
replaced, so nothing here reaches the network.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from pyforge.doctor.sources import bmad_method

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


# --- story 41.4: the real recipes' GitHub mapping (DW-FU-15-1-2) ---------------

#: The npm-invisible suite packages the GitHub fallback exists for, with the
#: owner/repo each real recipe must map to.
_LIVE_GITHUB_MAPPED = {
    "bmad-loop": "bmad-code-org/bmad-loop",
    "bmad-builder": "bmad-code-org/bmad-builder",
    "bmad-creative-intelligence-suite": "bmad-code-org/bmad-module-creative-intelligence-suite",
    "bmad-method-test-architecture-enterprise": "bmad-code-org/bmad-method-test-architecture-enterprise",
    "bmad-method-wds-expansion": "bmad-code-org/bmad-method-wds-expansion",
    "bmad-eval-quality": "bmad-code-org/bmad-eval-quality",
}


@pytest.mark.parametrize(("package", "owner_repo"), sorted(_LIVE_GITHUB_MAPPED.items()))
def test_the_real_recipe_resolves_through_the_github_fallback(
    monkeypatch: pytest.MonkeyPatch, package: str, owner_repo: str
) -> None:
    repo_root = Path(__file__).resolve().parents[6]
    recipe = repo_root / "recipes" / package / "recipe.yaml"
    # The live half runs only where the tree exists: an absent recipe is a failure, never a silent skip.
    assert recipe.is_file(), f"{recipe} is missing: the live-tree half needs the repository's own recipes"
    seen: list[str] = []

    def _urlopen(url: str, timeout: float | None = None) -> io.BytesIO:
        seen.append(url)
        return io.BytesIO(json.dumps({"tag_name": "v9.9.9"}).encode())

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)

    assert bmad_method._github_owner_repo(repo_root, package) == owner_repo
    assert bmad_method._resolve_upstream_latest(package, repo_root, timeout=1.0) == (9, 9, 9)
    assert seen == [f"https://api.github.com/repos/{owner_repo}/releases/latest"]
