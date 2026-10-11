"""Story 91.1: regenerate ``environment.yaml`` from the pixi exporter before verify."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyforge.core.process import ProcessPort

from . import dispatch as dispatch_core
from .commit_vcs import CommittingVcs
from .egress import to_redacted_text
from .refs import ORIGIN_MAIN

ENVIRONMENT_YAML_PATH = "environment.yaml"
PIXI_TOML_PATH = "pixi.toml"
ENVIRONMENT_YAML_EXPORT_COMMAND = "pixi project export conda-environment -e build"
_EXPORT_TOKENS = ("pixi", "project", "export", "conda-environment", "-e", "build")


@dataclass(frozen=True)
class DispatchEnvironmentYamlResult:
    """Outcome of the pre-verify ``environment.yaml`` regeneration pass."""

    paths: tuple[str, ...]
    committed: bool
    export_exit_code: int | None


def changed_files_trigger_environment_yaml_regeneration(
    changed_files: tuple[str, ...],
) -> bool:
    """Return whether the story diff against ``origin/main`` calls for regeneration."""
    return ENVIRONMENT_YAML_PATH in changed_files or PIXI_TOML_PATH in changed_files


def export_stdout_differs_from_file(*, export_stdout: str, file_text: str) -> bool:
    """Compare export stdout to on-disk text the way steward's sync check does."""
    return export_stdout.rstrip() != file_text.rstrip()


def apply_dispatch_environment_yaml_before_verify(
    *,
    worktree: Path,
    repo_root: Path,
    vcs: CommittingVcs,
    process: ProcessPort,
) -> DispatchEnvironmentYamlResult:
    """Regenerate ``environment.yaml`` from exporter stdout when the story diff requires it."""
    git_repo = dispatch_core.canonical_repo_root(repo_root)
    try:
        scope_changed = vcs.changed_files(git_repo, worktree, base=ORIGIN_MAIN)
    except Exception:
        return DispatchEnvironmentYamlResult((), False, None)

    if not changed_files_trigger_environment_yaml_regeneration(scope_changed):
        return DispatchEnvironmentYamlResult((), False, None)

    env_path = worktree / ENVIRONMENT_YAML_PATH
    result = process.run(list(_EXPORT_TOKENS), cwd=worktree)

    if result.returncode != 0:
        return DispatchEnvironmentYamlResult((ENVIRONMENT_YAML_PATH,), False, result.returncode)

    export_text = result.stdout
    if env_path.is_file():
        on_disk = env_path.read_text(encoding="utf-8")
    else:
        on_disk = ""

    if not export_stdout_differs_from_file(export_stdout=export_text, file_text=on_disk):
        return DispatchEnvironmentYamlResult((ENVIRONMENT_YAML_PATH,), False, result.returncode)

    env_path.write_text(export_text, encoding="utf-8")

    try:
        vcs.commit_paths(
            worktree,
            (Path(ENVIRONMENT_YAML_PATH),),
            to_redacted_text("marshal: regenerate environment.yaml from pixi export (Story 91.1)"),
        )
    except Exception:
        return DispatchEnvironmentYamlResult((ENVIRONMENT_YAML_PATH,), False, result.returncode)

    return DispatchEnvironmentYamlResult((ENVIRONMENT_YAML_PATH,), True, result.returncode)
