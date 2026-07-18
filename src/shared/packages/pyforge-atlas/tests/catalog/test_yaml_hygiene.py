"""Review-pass patch (2026-07-17): duplicate-key guard on the conf YAMLs.

PyYAML (and permissive loaders) silently keep the LAST occurrence of a
duplicated mapping key, so a duplicate catalog entry / override point could
skew the pinned counts without any test failing. A real duplicate-key
incident (BIGQUERY_BASE_URL doubled in globals.yml by a racing edit)
occurred during this story's implementation — this guard makes the class
impossible to ship (same failure class as CFE gotcha G92).
"""

from __future__ import annotations

import yaml

from .conftest import CATALOG_YML, GLOBALS_YML, PARAMETERS_YML


class _DuplicateKeyError(Exception):
    pass


class _DupSafeLoader(yaml.SafeLoader):
    pass


def _construct_mapping_no_dupes(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise _DuplicateKeyError(
                f"duplicate key {key!r} at line {key_node.start_mark.line + 1}"
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_DupSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_no_dupes
)


def _assert_no_duplicate_keys(path):
    try:
        yaml.load(path.read_text(encoding="utf-8"), Loader=_DupSafeLoader)
    except _DuplicateKeyError as exc:
        raise AssertionError(f"{path.name}: {exc}") from exc


def test_catalog_yaml_has_no_duplicate_keys():
    _assert_no_duplicate_keys(CATALOG_YML)


def test_globals_yaml_has_no_duplicate_keys():
    _assert_no_duplicate_keys(GLOBALS_YML)


def test_parameters_yaml_has_no_duplicate_keys():
    _assert_no_duplicate_keys(PARAMETERS_YML)
