"""Meta test -- the NFR-9 contract guard for ``bmad-loop probe-adapter
--json``'s own document shape (Story 6.4, FR-43).

``adapters/harness_bmadloop.py::BmadLoopHarness.adapter_probe`` stores this
document VERBATIM (opaque, never parsed -- see the story's own spec Design
Notes for why), so Marshal never notices a silent upstream shape change on
its own. No shape-pinning idiom already existed in this codebase for "fails
loudly on upstream drift" (researched directly: no ``SCHEMA_VERSION``/
``dataclasses.fields``/"contract test" precedent anywhere under
``tests/meta/`` or ``tests/unit/test_harness_bmadloop_*.py`` -- the closest
sibling, ``HARNESS_VERSION_RANGE_TEXT``, pins a VERSION NUMBER, not a
document SHAPE). This test imports the REAL installed ``bmad_loop.probe``
module directly -- a test-only exception to AD-3's "only ``adapters/
harness_bmadloop.py`` imports ``bmad_loop``" rule, mirroring the SAME
exception ``tests/meta/test_ad34_egress_registry_completeness.py`` already
takes to inspect package internals -- and asserts, character-for-character,
the ``SCHEMA_VERSION`` constant and the exact key set ``render_json``
produces. Either changing means this test fails BEFORE any downstream
story (6.5's smoke run, 6.6's matrix) is misled by a silently-reshaped
``probe_output``.
"""

from __future__ import annotations

from bmad_loop import probe

# Confirmed live against the installed 0.9.0 package, 2026-08-07 (see this
# story's own spec, Design Notes and Code Map). A bump means the JSON
# document's own shape changed and `adapter_probe`'s own docstring/this
# story's Design Notes must be revisited before trusting `probe_output`'s
# contents downstream.
_EXPECTED_SCHEMA_VERSION = 2

_EXPECTED_KEYS = frozenset(
    {
        "schema_version",
        "cli",
        "mode",
        "known_profile",
        "binary",
        "binary_found",
        "dialect",
        "usage_parser",
        "hooks_registered",
        "declared_events",
        "version",
        "help",
        "captured_events",
        "transcript",
        "tokens",
        "warnings",
        "next_steps",
    }
)


def test_probe_schema_version_matches_the_pinned_value():
    assert probe.SCHEMA_VERSION == _EXPECTED_SCHEMA_VERSION, (
        "bmad_loop.probe.SCHEMA_VERSION changed -- probe-adapter --json's own "
        "document shape may have changed too; re-verify adapter_probe's own "
        "docstring and this story's Design Notes before trusting probe_output"
    )


def test_probe_json_document_has_exactly_the_pinned_key_set():
    import json

    finding = probe.ProfileFinding(
        cli="claude", mode="scan", known_profile=True, binary="claude", parser="none"
    )
    document = json.loads(probe.render_json(finding))
    assert set(document.keys()) == _EXPECTED_KEYS, (
        "bmad-loop probe-adapter --json's own key set drifted from what this "
        "package pins -- a key was added, renamed, or removed upstream"
    )
