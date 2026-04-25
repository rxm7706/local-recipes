"""Unit tests for mapping_manager.py (incl. fix #3 regression)."""
from __future__ import annotations


class TestMappingManager:
    def test_uses_conda_forge_metadata_not_grayskull(self, load_module):
        """Fix #3 regression: the script no longer hits the dead
        grayskull URL. It should use conda_forge_metadata."""
        mod = load_module("mapping_manager.py")
        assert hasattr(mod, "fetch_conda_forge_metadata_mapping")
        assert not hasattr(mod, "fetch_grayskull_mapping"), (
            "Fix #3 should have removed the dead Grayskull URL fetcher. "
            "Found `fetch_grayskull_mapping` still present."
        )
        # Constant should NOT exist anymore
        assert not hasattr(mod, "GRAYSKULL_MAPPING_URL")

    def test_fetch_returns_lowercased_dict(
        self, load_module, stub_metadata_api
    ):
        mod = load_module("mapping_manager.py")
        result = mod.fetch_conda_forge_metadata_mapping()
        assert isinstance(result, dict)
        # Stub registers `pillow` (already lowercase) and `21cmfast`
        assert result.get("pillow") == "pillow"
        assert result.get("21cmfast") == "21cmfast"
        # All keys lowercased
        assert all(k == k.lower() for k in result.keys())

    def test_metadata_unavailable_branch(self, load_module, monkeypatch):
        """When conda_forge_metadata is unavailable, fetch should raise."""
        mod = load_module("mapping_manager.py")
        monkeypatch.setattr(mod, "METADATA_AVAILABLE", False)
        monkeypatch.setattr(mod, "get_pypi_name_mapping", None)
        try:
            mod.fetch_conda_forge_metadata_mapping()
        except ImportError:
            return
        raise AssertionError("Expected ImportError when METADATA_AVAILABLE is False")
