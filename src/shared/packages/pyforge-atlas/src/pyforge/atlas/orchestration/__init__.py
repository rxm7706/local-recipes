"""``kedro-dagster`` orchestration glue subpackage (Story C1, FR-6).

This is the ONE place in the ``pyforge.atlas`` package that is allowed to
import ``dagster`` / ``kedro_dagster`` (AD-1 / AD-6: replaceable orchestration
glue, no upward imports). The rest of the package — pipelines, nodes,
datasets, mcp — MUST NOT import either library; the AD-1 import-ban AST test
(``tests/catalog/test_no_inline_io.py::test_ad1_import_direction`` +
``test_dagster_only_in_glue``) enforces that, exempting only
``orchestration/definitions.py``.

The subpackage is named ``orchestration`` (NOT ``dagster``) on purpose: a
subpackage literally named ``dagster`` shadows the top-level ``dagster``
dependency under pytest's import modes, so the neutral name keeps
``import dagster`` inside the glue unambiguous.

Kept intentionally empty of heavy imports: importing
``pyforge.atlas.orchestration`` must stay cheap and must NOT pull in
``dagster``. The definitions live in the sibling
:mod:`pyforge.atlas.orchestration.definitions` module (imported by Dagster
tooling and the ``dagster-dryrun`` gate, never at package import time).
"""

from __future__ import annotations
