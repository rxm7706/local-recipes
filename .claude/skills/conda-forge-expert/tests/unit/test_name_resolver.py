"""Unit tests for name_resolver.py (incl. fix #3 regression)."""
from __future__ import annotations

import json


class TestNameResolver:
    def test_resolves_identity_via_metadata_api(
        self, load_module, stub_metadata_api
    ):
        """Fix #3 regression: bulk mapping omits identity entries; the
        metadata-api tier must catch them."""
        mod = load_module("name_resolver.py")
        # `Pillow` lower-cases to `pillow`; stub maps pillow → pillow
        result = mod.resolve_name("Pillow")
        assert result["success"] is True
        assert result["conda_name"] == "pillow"
        assert result["source"] in ("local-cache", "metadata-api")

    def test_metadata_api_tier_exists(self, load_module):
        """Fix #3 added Tier 2 (metadata-api). Validate the function is wired."""
        mod = load_module("name_resolver.py")
        assert hasattr(mod, "search_metadata_api"), (
            "Fix #3 should expose `search_metadata_api`."
        )

    def test_local_cache_priority(self, load_module, monkeypatch, tmp_path):
        """Local cache should be checked before the metadata API."""
        mod = load_module("name_resolver.py")
        cache_file = tmp_path / "pypi_conda_map.json"
        cache_file.write_text(json.dumps({"foo": "foo-conda-cached"}))
        monkeypatch.setattr(mod, "MAPPING_CACHE_FILE", cache_file)

        result = mod.resolve_name("foo")
        assert result["source"] == "local-cache"
        assert result["conda_name"] == "foo-conda-cached"

    def test_normalize_name(self, load_module):
        mod = load_module("name_resolver.py")
        assert mod.normalize_name("Python_DateUtil") == "python-dateutil"
        assert mod.normalize_name("PyYAML") == "pyyaml"

    def test_unknown_via_api_falls_back_to_input(
        self, load_module, stub_metadata_api, monkeypatch, tmp_path
    ):
        """Per fix #3 caveat: unknown names get identity-fallback (the API
        does this, not the script). This is documented behaviour."""
        mod = load_module("name_resolver.py")
        # Force an empty cache so we go straight to the metadata API
        empty_cache = tmp_path / "empty.json"
        empty_cache.write_text("{}")
        monkeypatch.setattr(mod, "MAPPING_CACHE_FILE", empty_cache)
        result = mod.resolve_name("nonexistent-pkg")
        # The stub returns the input unchanged for unknown names
        assert result["success"] is True
        assert result["conda_name"] == "nonexistent-pkg"
