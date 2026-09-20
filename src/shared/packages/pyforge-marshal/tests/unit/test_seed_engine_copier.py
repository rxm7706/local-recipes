"""Real-Copier tests for `seed/engine/copier.py` (Story 10.1) -- exercises
`copier==9.17.1` for real against throwaway, hand-built fixture templates
under `tmp_path`, mirroring Spike-0's own method
(`spike-0-copier-api-fit-report.md`: a git-backed template with a
`copier.yml`, an `{{ _copier_conf.answers_file }}.jinja` file, and a
tagged commit history for the update/recopy scenarios). No
`copier.run_copy`/`run_update`/`run_recopy` call is ever mocked -- every
scenario below drives the real library.

A few of these tests (the UPDATE/RECOPY fixture setup) call `copier.run_copy`
DIRECTLY to bootstrap a realistic "already materialized once" destination --
Story 10.3's apply runner (which would normally have produced that state)
doesn't exist yet. That is fixture SETUP, not the thing under test: every
assertion about `materialize()`'s own behavior goes exclusively through the
`pyforge.marshal.seed.engine.copier` wrapper, matching Spike-0's own
precedent of driving the real library directly in throwaway spike/test code
outside of any wrapper. P-02 ("copier is imported nowhere in the codebase
except seed/engine/copier.py") governs the INSTALLED PACKAGE, not test
files -- the dedicated meta test
(`tests/meta/test_p02_copier_sole_ownership.py`) scans only the installed
`pyforge.marshal` package directory, which never includes this file.
"""

from __future__ import annotations

import re
import subprocess
from importlib import resources
from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.seed.engine.copier import (
    CopierEngineError,
    MaterializeRequest,
    MaterializeResult,
    MaterializeVerb,
    TemplateBoundaryError,
    _template_source,
    materialize,
)

# --- fixture-building helpers ------------------------------------------------


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", cwd=path)
    _git("config", "user.email", "test@example.com", cwd=path)
    _git("config", "user.name", "Test", cwd=path)


def _write_answers_file_shim(template_dir: Path) -> None:
    # Spike-0 Finding 1: Copier does not auto-generate the answers file --
    # the TEMPLATE must ship this literal file for it to come into existence.
    (template_dir / "{{ _copier_conf.answers_file }}.jinja").write_text(
        "{{ _copier_answers|to_nice_yaml -}}\n", encoding="utf-8"
    )


def _write_copier_yml(template_dir: Path, *, tasks: bool = False) -> None:
    body = "_answers_file: .marshal/.copier-answers.yml\nproject_name:\n  type: str\n  default: demo\n"
    if tasks:
        # `_tasks:` is Copier's own unsafe-feature trigger (verified
        # empirically for this story: refuses with UnsafeTemplateError
        # unless unsafe=True). Appends to AGENTS.md (already manifest
        # allow-listed) rather than writing a brand-new path -- this
        # scenario is about the unsafe-feature refusal, not the boundary
        # check, and a stray out-of-manifest task artifact would trip that
        # unrelated check instead.
        body += '_tasks:\n  - "echo task-ran >> AGENTS.md"\n'
    (template_dir / "copier.yml").write_text(body, encoding="utf-8")


def _build_fresh_copy_template(root: Path) -> Path:
    template_dir = root / "tmpl"
    template_dir.mkdir(parents=True)
    _write_copier_yml(template_dir)
    _write_answers_file_shim(template_dir)
    (template_dir / "AGENTS.md.jinja").write_text("# {{ project_name }}\n", encoding="utf-8")
    return template_dir


def _build_unsafe_template(root: Path) -> Path:
    template_dir = root / "tmpl-unsafe"
    template_dir.mkdir(parents=True)
    _write_copier_yml(template_dir, tasks=True)
    _write_answers_file_shim(template_dir)
    (template_dir / "AGENTS.md.jinja").write_text("# {{ project_name }}\n", encoding="utf-8")
    return template_dir


def _build_out_of_manifest_template(root: Path) -> Path:
    template_dir = root / "tmpl-oob"
    template_dir.mkdir(parents=True)
    _write_copier_yml(template_dir)
    _write_answers_file_shim(template_dir)
    (template_dir / "unmanifested-file.txt.jinja").write_text("hi {{ project_name }}\n", encoding="utf-8")
    return template_dir


def _build_versioned_template_repo(root: Path) -> Path:
    """A git-backed template with two tagged commits (v1.0.0 -> v2.0.0),
    mirroring Spike-0's own AC5 method -- the shape `UPDATE`/`RECOPY` need
    to have real history to diff against."""
    template_dir = root / "tmpl-versioned"
    _init_git_repo(template_dir)
    _write_copier_yml(template_dir)
    _write_answers_file_shim(template_dir)
    (template_dir / "AGENTS.md.jinja").write_text("# {{ project_name }} v1\n", encoding="utf-8")
    _git("add", "-A", cwd=template_dir)
    _git("commit", "-q", "-m", "v1", cwd=template_dir)
    _git("tag", "v1.0.0", cwd=template_dir)

    (template_dir / "AGENTS.md.jinja").write_text("# {{ project_name }} v2\n", encoding="utf-8")
    _git("add", "-A", cwd=template_dir)
    _git("commit", "-q", "-m", "v2", cwd=template_dir)
    _git("tag", "v2.0.0", cwd=template_dir)
    return template_dir


def _bootstrap_existing_destination(template_dir: Path, dst_path: Path) -> None:
    """Build a realistic "already materialized once, at v1.0.0" destination
    -- fixture SETUP only (see module docstring): calls `copier.run_copy`
    directly because Story 10.3's apply runner (which would normally have
    produced this state from a prior `materialize()` call) doesn't exist
    yet, and `materialize()` itself never writes `dst_path` -- there is no
    other way to get a realistic pre-existing destination for the
    UPDATE/RECOPY scenarios."""
    import copier as real_copier

    real_copier.run_copy(
        str(template_dir),
        dst_path,
        data={"project_name": "demo"},
        defaults=True,
        overwrite=True,
        quiet=True,
        answers_file=".marshal/.copier-answers.yml",
        vcs_ref="v1.0.0",
    )
    _init_git_repo(dst_path)
    _git("add", "-A", cwd=dst_path)
    _git("commit", "-q", "-m", "initial (v1.0.0)", cwd=dst_path)


# --- I/O matrix: fresh copy ---------------------------------------------------


def test_fresh_copy_stages_without_touching_the_live_destination(tmp_path):
    template_dir = _build_fresh_copy_template(tmp_path)
    dst_path = tmp_path / "dst"  # does not exist

    result = materialize(
        MaterializeRequest(
            verb=MaterializeVerb.COPY,
            dst_path=dst_path,
            template_path=template_dir,
            data={"project_name": "demo-copy"},
        )
    )

    assert not dst_path.exists()
    assert isinstance(result, MaterializeResult)
    names = {path.name for path in result.staged_paths}
    assert names == {"AGENTS.md", ".copier-answers.yml"}
    agents_md = next(path for path in result.staged_paths if path.name == "AGENTS.md")
    assert agents_md.read_text(encoding="utf-8") == "# demo-copy\n"
    assert result.answers == {"project_name": "demo-copy"}


def test_fresh_copy_with_explicit_template_path_as_str(tmp_path):
    template_dir = _build_fresh_copy_template(tmp_path)
    dst_path = tmp_path / "dst"

    result = materialize(
        MaterializeRequest(
            verb=MaterializeVerb.COPY,
            dst_path=dst_path,
            template_path=str(template_dir),
            data={"project_name": "demo"},
        )
    )
    assert any(path.name == "AGENTS.md" for path in result.staged_paths)


# --- I/O matrix: update -------------------------------------------------------


def test_update_against_an_existing_answers_file_succeeds(tmp_path):
    template_dir = _build_versioned_template_repo(tmp_path)
    dst_path = tmp_path / "dst"
    _bootstrap_existing_destination(template_dir, dst_path)

    assert (dst_path / ".marshal" / ".copier-answers.yml").exists()
    old_content = (dst_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "v1" in old_content

    # Spike-0's own failure mode (`TypeError: Template not found`) fires
    # when `answers_file=` is omitted from `run_update` -- materialize()
    # always passes it explicitly, so this must succeed.
    result = materialize(
        MaterializeRequest(
            verb=MaterializeVerb.UPDATE,
            dst_path=dst_path,
            data={"project_name": "demo"},
        )
    )

    staged_agents = next(path for path in result.staged_paths if path.name == "AGENTS.md")
    assert "v2" in staged_agents.read_text(encoding="utf-8")
    # the live destination is never touched by materialize()
    assert (dst_path / "AGENTS.md").read_text(encoding="utf-8") == old_content


def test_update_omitting_answers_file_would_fail_without_the_wrapper(tmp_path):
    """Non-vacuous proof that the wrapper's explicit `answers_file=` is
    load-bearing, not incidental: the SAME destination, driven through the
    real library WITHOUT it (fixture-style direct call, matching Spike-0's
    own reproduction), reproduces Spike-0's `TypeError: Template not
    found`."""
    import copier as real_copier

    template_dir = _build_versioned_template_repo(tmp_path)
    dst_path = tmp_path / "dst"
    _bootstrap_existing_destination(template_dir, dst_path)

    with pytest.raises(TypeError, match="Template not found"):
        real_copier.run_update(dst_path, defaults=True, overwrite=True, quiet=True)


# --- I/O matrix: recopy without confirm ---------------------------------------


def test_recopy_without_confirm_raises_before_invoking_copier(tmp_path):
    dst_path = tmp_path / "dst"  # never created/touched
    request = MaterializeRequest(verb=MaterializeVerb.RECOPY, dst_path=dst_path, confirm=False)

    with pytest.raises(CopierEngineError, match="confirm"):
        materialize(request)

    assert not dst_path.exists()


def test_recopy_with_confirm_succeeds_and_reflects_only_changed_paths(tmp_path):
    """Bonus coverage beyond the required matrix row: proves the RECOPY
    execution branch (including the git-status-diff staged-path detection)
    actually works, and that a pre-existing, untouched committed file is
    correctly excluded from the result."""
    template_dir = _build_versioned_template_repo(tmp_path)
    dst_path = tmp_path / "dst"
    _bootstrap_existing_destination(template_dir, dst_path)
    (dst_path / "README.md").write_text("unrelated\n", encoding="utf-8")
    _git("add", "-A", cwd=dst_path)
    _git("commit", "-q", "-m", "unrelated", cwd=dst_path)

    result = materialize(
        MaterializeRequest(
            verb=MaterializeVerb.RECOPY,
            dst_path=dst_path,
            data={"project_name": "demo"},
            confirm=True,
        )
    )

    names = {path.name for path in result.staged_paths}
    assert "README.md" not in names
    assert (dst_path / "README.md").exists()  # live dst untouched


# --- I/O matrix: unsafe feature -----------------------------------------------


def test_unsafe_feature_without_unsafe_flag_raises_copier_engine_error(tmp_path):
    template_dir = _build_unsafe_template(tmp_path)
    dst_path = tmp_path / "dst"
    request = MaterializeRequest(
        verb=MaterializeVerb.COPY,
        dst_path=dst_path,
        template_path=template_dir,
        data={"project_name": "demo"},
    )

    with pytest.raises(CopierEngineError) as excinfo:
        materialize(request)

    assert not isinstance(excinfo.value, TemplateBoundaryError)
    assert not dst_path.exists()


def test_unsafe_feature_with_unsafe_true_succeeds(tmp_path):
    template_dir = _build_unsafe_template(tmp_path)
    dst_path = tmp_path / "dst"

    result = materialize(
        MaterializeRequest(
            verb=MaterializeVerb.COPY,
            dst_path=dst_path,
            template_path=template_dir,
            data={"project_name": "demo"},
            unsafe=True,
        )
    )

    agents_md = next(path for path in result.staged_paths if path.name == "AGENTS.md")
    assert "task-ran" in agents_md.read_text(encoding="utf-8")


# --- I/O matrix: out-of-manifest write ----------------------------------------


def test_out_of_manifest_write_raises_template_boundary_error_naming_the_path(tmp_path):
    template_dir = _build_out_of_manifest_template(tmp_path)
    dst_path = tmp_path / "dst"
    request = MaterializeRequest(
        verb=MaterializeVerb.COPY,
        dst_path=dst_path,
        template_path=template_dir,
        data={"project_name": "demo"},
    )

    with pytest.raises(TemplateBoundaryError, match="unmanifested-file.txt"):
        materialize(request)

    assert not dst_path.exists()


def test_genesis_owned_path_and_a_real_manifest_entry_both_pass_the_boundary(tmp_path):
    """The answers file (`_GENESIS_OWNED_PATHS`, no manifest entry) and
    `AGENTS.md` (a real `hybrid-managed-region` manifest entry) both clear
    the boundary check in the same render -- proves the allow-list is a
    UNION, not either set alone."""
    template_dir = _build_fresh_copy_template(tmp_path)
    dst_path = tmp_path / "dst"
    result = materialize(
        MaterializeRequest(
            verb=MaterializeVerb.COPY,
            dst_path=dst_path,
            template_path=template_dir,
            data={"project_name": "demo"},
        )
    )
    relative_names = {path.name for path in result.staged_paths}
    assert relative_names == {"AGENTS.md", ".copier-answers.yml"}


# --- default template resolution ----------------------------------------------


def test_default_template_source_resolves_to_the_packaged_templates_dir():
    expected_root = resources.files("pyforge.marshal.seed.templates")
    with resources.as_file(expected_root) as expected_path, _template_source(None) as actual:
        assert Path(actual).resolve() == expected_path.resolve()


def test_explicit_template_source_passes_through_unchanged(tmp_path):
    with _template_source(tmp_path) as actual:
        assert actual == str(tmp_path)
    with _template_source("https://example.invalid/repo.git") as actual:
        assert actual == "https://example.invalid/repo.git"


# --- P-02 belt-and-suspenders: plain-text scan (independent of the AST meta test) --


_IMPORT_LINE_RE = re.compile(r"^(import\s+copier\b|from\s+copier\b)")


def test_import_copier_only_appears_in_the_engine_module():
    package_dir = Path(pyforge.marshal.__file__).resolve().parent
    engine_module = package_dir / "seed" / "engine" / "copier.py"
    assert engine_module.exists()

    offenders: list[str] = []
    for path in sorted(package_dir.rglob("*.py")):
        if path == engine_module:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if _IMPORT_LINE_RE.match(line.strip()):
                offenders.append(str(path.relative_to(package_dir)))
                break
    assert offenders == []
