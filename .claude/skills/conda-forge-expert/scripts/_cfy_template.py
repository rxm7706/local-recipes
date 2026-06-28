"""Shared renderer for the universal ``conda-forge.yml`` pre-seed.

The emitted file is **inert** in the staged-recipes PR (``build_all.py`` reads
only ``conda_build_tool``) and is **forwarded** into the feedstock on merge — it
pre-seeds the feedstock so no post-merge bot/tooling/platform-expansion PR is
needed (CFE gotcha G83). Used by ``recipe-generator.py`` (generation) and
``submit_pr.py`` (emit-if-missing at submission). Keep both call sites in sync
by routing through this one renderer — do not hard-fork the content.

**Comment convention (mirrors the recipe.yaml cfe block):** the top of the file
carries only the trim one-line ``# conda-forge.yml — pre-seeds the feedstock``
comment + the keys (this is what gets submitted to staged-recipes / pushed to a
feedstock). The verbose rationale lives in a bottom ``#### CFE metadata AND
comments`` block that is **local-recipes-only and STRIPPED before push** (same as
recipe.yaml's ``#### CFE`` block — see G62). Keep the bottom comment free of the
literal key names the generator tests assert-absent (``build_platform:``,
``provider:``, ``run_deps_from_wheel``, ``workflow_settings``, ``error_overlinking``,
``shellcheck``).
"""

from __future__ import annotations


def render_conda_forge_yml(
    *,
    compiled: bool,
    noarch_python: bool,
    python_wheel: bool,
    feedstock: bool = False,
) -> str:
    """Render the universal ``conda-forge.yml`` pre-seed (trim top + bottom CFE block).

    Args:
        compiled: per-platform compiled recipe (maturin/PyO3, compiled-C/C++,
            Go, Rust-CLI, compiled CRAN/CPAN/LuaRocks). Adds the ARM platform
            matrix (``build_platform`` + ``provider`` + ``test``). noarch
            (python/generic) and npm omit it (one artifact / per-platform JS).
        noarch_python: noarch:python recipe → ``bot.inspection: update-grayskull``;
            everything else → ``hint-all`` (grayskull is PyPI-only — it mangles
            hand-tuned compiled/maturin host pins and is a no-op for npm/Go/CRAN).
        python_wheel: Python wheel-producing recipe (noarch:python + maturin) →
            emit ``bot.run_deps_from_wheel: true``; omit for npm/Go/CRAN (no wheel).
        feedstock: emit the feedstock-root-only keys
            (``conda_forge_output_validation`` + ``github.*``) for a direct
            ``<pkg>-feedstock`` file; omit for the staged-recipes per-recipe file
            (those are auto-stamped at feedstock creation).

    Never emits ``workflow_settings``, ``conda_build.error_overlinking``, or
    ``shellcheck`` — per the Jun-2026 per-setting audit they are no-op /
    convenience-only / inert for these recipe shapes.
    """
    inspection = "update-grayskull" if noarch_python else "hint-all"
    # --- Submitted portion: trim comment + keys -------------------------------
    lines = [
        "# conda-forge.yml — pre-seeds the feedstock",
        "conda_build_tool: rattler-build",
        "conda_install_tool: pixi",
    ]
    if feedstock:
        lines += [
            "conda_forge_output_validation: true",
            "github:",
            "  branch_name: main",
            "  tooling_branch_name: main",
        ]
    lines += [
        "bot:",
        "  automerge: true",
        "  check_solvable: true",
        f"  inspection: {inspection}",
    ]
    if python_wheel:
        lines.append("  run_deps_from_wheel: true")
    if compiled:
        lines += [
            "build_platform:",
            "  linux_aarch64: linux_64",
            "  osx_arm64: osx_64",
            "provider:",
            "  linux_aarch64: azure",
            "  osx_arm64: azure",
            "test: native_and_emulated",
        ]
    # --- Local-recipes-only detail: STRIPPED before push (G62) ----------------
    # NB: keep this comment free of the literal key strings the generator tests
    # assert-absent (build_platform:/provider:/run_deps_from_wheel/...).
    lines += [
        "",
        "#### CFE metadata AND comments",
        "# CFE comments",
        "#    # Pre-seeds the feedstock (CFE skill default, G83): these keys are INERT",
        "#    # in the staged-recipes PR (build_all.py reads only conda_build_tool) and",
        "#    # are forwarded into the feedstock on merge, so no post-merge bot / tooling",
        "#    # / platform-expansion PR is needed. The universal block (build tools + bot",
        "#    # policy) applies to every recipe; COMPILED recipes also carry the ARM",
        "#    # platform matrix above (trim it to the arches the recipe actually builds —",
        "#    # drop any its `skip:` excludes; e.g. an osx-arm64-only recipe keeps just",
        "#    # the osx_arm64 leg). This #### CFE block is local-recipes-only and is",
        "#    # STRIPPED before push (same convention as recipe.yaml's cfe block, G62) —",
        "#    # the submitted staged-recipes / feedstock file is just the trim top",
        "#    # comment + the keys above.",
        "####",
    ]
    return "\n".join(lines) + "\n"
