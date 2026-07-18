"""Story A1 `kedro-test` gate: import smokes + the Kedro-in-namespace-package seam.

Permanent Wave-A tests (AD-11): fixture-based, non-credentialed, offline.
- (a) `import pyforge.atlas` — the dotted PEP 420 namespace package (AC-7).
- (b) `import pyforge.warden` — proves both namespace members import side by side.
- (c) `import kedro_dagster` — the py3.14-unclassified glue AD-16 names
      (solve-asserted only until this import runs).
- (d) the Kedro bootstrap/session seam on the dotted `package_name` (Task 2.2).
"""
from pathlib import Path

MEMBER_DIR = Path(__file__).resolve().parents[1]


def test_import_pyforge_atlas():
    import pyforge.atlas  # noqa: F401


def test_import_pyforge_warden_beside_atlas():
    import pyforge.atlas  # noqa: F401
    import pyforge.warden  # noqa: F401


def test_import_kedro_dagster_glue():
    import kedro_dagster  # noqa: F401


def test_kedro_bootstrap_resolves_dotted_package():
    """Kedro must resolve the dotted `pyforge.atlas` package_name (AC-7 seam)."""
    from kedro.framework.startup import bootstrap_project

    metadata = bootstrap_project(MEMBER_DIR)
    assert metadata.package_name == "pyforge.atlas"
    assert metadata.project_name == "pyforge-atlas"


def test_kedro_session_creates_and_loads_context():
    """KedroSession.create + load_context on the namespace-package project."""
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project

    bootstrap_project(MEMBER_DIR)
    with KedroSession.create(project_path=MEMBER_DIR) as session:
        context = session.load_context()
        # settings.py resolved through the dotted package; catalog loads (empty
        # until A2 populates conf/base/catalog.yml).
        assert context.project_path == MEMBER_DIR
