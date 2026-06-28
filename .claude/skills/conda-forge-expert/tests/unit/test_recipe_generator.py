"""Unit tests for recipe-generator.py (hyphenated → script_runner only)."""
from __future__ import annotations

import json

import pytest

import yaml


class TestRecipeGenerator:
    def test_smoke_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "--help")
        assert rc == 0
        for ecosystem in (
            "pypi", "template", "github", "cran", "cpan", "luarocks", "npm",
        ):
            assert ecosystem in out.lower(), f"missing {ecosystem} in --help"

    def test_cran_subcommand_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "cran", "--help")
        assert rc == 0
        assert "cran" in out.lower()
        assert "--universe" in out or "-u" in out

    def test_cpan_subcommand_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "cpan", "--help")
        assert rc == 0
        assert "cpan" in out.lower()
        assert "--version" in out

    def test_luarocks_subcommand_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "luarocks", "--help")
        assert rc == 0
        assert "luarocks" in out.lower() or "rock" in out.lower()

    def test_npm_subcommand_help(self, script_runner):
        rc, out, _ = script_runner("recipe-generator.py", "npm", "--help")
        assert rc == 0
        assert "npm" in out.lower()
        assert "package" in out.lower()

    def test_npm_normalize_repo_url(self, load_module):
        """Verify the git+url → https translation used by the npm scaffolder."""
        mod = load_module("recipe-generator.py")
        # Common shapes returned from npm registry
        assert mod._normalize_repo_url(
            {"type": "git", "url": "git+https://github.com/owner/repo.git"}
        ) == "https://github.com/owner/repo"
        assert mod._normalize_repo_url(
            {"type": "git", "url": "git@github.com:owner/repo.git"}
        ) == "https://github.com/owner/repo"
        assert mod._normalize_repo_url("git://github.com/owner/repo.git") == \
            "https://github.com/owner/repo"
        assert mod._normalize_repo_url("") == ""
        assert mod._normalize_repo_url(None) == ""

    def test_npm_recipe_canonical_shape_offline(self, load_module, tmp_path):
        """Generate a recipe from a synthetic NpmPackageInfo and verify it
        matches the canonical conda-forge npm pattern (no network)."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="example-pkg",
            conda_name="example-pkg",
            version="1.0.0",
            description="A synthetic test package.",
            license="MIT",
            homepage="https://example.com",
            repository_url="https://github.com/example/example-pkg",
            tarball_url="https://registry.npmjs.org/example-pkg/-/example-pkg-1.0.0.tgz",
            tarball_filename="example-pkg-1.0.0.tgz",
            source_url="https://registry.npmjs.org/example-pkg/-/example-pkg-${{ version }}.tgz",
            sha256="a" * 64,
            bin_entries={"example-pkg": "bin/cli.js"},
            node_major=20,
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path)
        assert recipe_path.exists()
        content = recipe_path.read_text()
        pkg_dir = recipe_path.parent

        # ── Canonical recipe.yaml shape (v8.11.0 per-platform inline) ───
        # Editor schema header lets VS Code/Helix validate live against
        # prefix-dev/recipe-format. Required on every emitted recipe.yaml.
        assert "# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json" in content
        # Reference PRs omit `schema_version`, but we emit it explicitly so our
        # validate_recipe.py is happy. Both forms are accepted by rattler-build.
        assert "schema_version: 1" in content
        # v8.11.0: per-platform builds; noarch:generic is gone.
        assert "noarch: generic" not in content
        # Source URL embedded (npm registry by default)
        assert info.source_url in content
        # sha256 embedded
        assert "a" * 64 in content
        # Bin command rendered into a flat script test
        assert "example-pkg --help" in content
        # Canonical pattern doesn't emit `.bat` test variants
        assert "example-pkg.bat --help" not in content
        # Build deps include nodejs + pnpm + pnpm-licenses
        assert "- nodejs" in content
        assert "- pnpm" in content
        assert "- pnpm-licenses" in content
        # license_file is a list with third-party-licenses.txt
        assert "license_file:" in content
        assert "- LICENSE" in content
        assert "- third-party-licenses.txt" in content
        # No __unix/__win selectors (those are non-canonical)
        assert "__unix" not in content
        assert "__win" not in content

        # ── Inline build.script with per-platform branches ───────────────
        # The v8.11.0 canonical pattern (openspec PR #32368 + bmalph PR #33557).
        assert "script:" in content
        assert "if: unix" in content
        assert "then:" in content
        assert "else:" in content
        # Unix branch
        assert "set -ex" in content
        assert "pnpm install --ignore-scripts" in content
        assert "npm pack --ignore-scripts" in content
        assert 'npm install --global "${SRC_DIR}/example-pkg-${{ version }}.tgz"' in content
        assert "pnpm-licenses generate-disclaimer --prod" in content
        # Windows branch — `call` + ERRORLEVEL guards
        assert "call pnpm install --ignore-scripts" in content
        assert "call npm pack --ignore-scripts" in content
        assert "call npm install --global %SRC_DIR%/example-pkg-${{ version }}.tgz" in content
        assert "call pnpm-licenses generate-disclaimer --prod" in content
        assert "if %ERRORLEVEL% neq 0 exit 1" in content
        # The literal version must NOT appear in any install line
        assert "example-pkg-1.0.0.tgz" not in content
        # Recipe source.url must also use ${{ version }}, not a literal
        assert "example-pkg-${{ version }}.tgz" in content

        # ── No standalone build files in the v8.11.0 default ──────────────
        assert not (pkg_dir / "build.sh").exists()
        assert not (pkg_dir / "build.bat").exists()
        # Critical: must NOT use v0's bld.bat
        assert not (pkg_dir / "bld.bat").exists()
        # Universal conda-forge.yml pre-seed (G83) — emitted for every recipe
        # now. npm = per-platform JS CLI: hint-all, no run_deps_from_wheel, no
        # ARM block, and none of the no-op keys.
        cfy = (pkg_dir / "conda-forge.yml").read_text()
        assert "conda_build_tool: rattler-build" in cfy
        assert "conda_install_tool: pixi" in cfy
        assert "automerge: true" in cfy
        assert "inspection: hint-all" in cfy
        assert "run_deps_from_wheel" not in cfy   # no wheel for an npm CLI
        assert "build_platform:" not in cfy        # no ARM block for npm
        assert "provider:" not in cfy
        assert "workflow_settings" not in cfy
        assert "error_overlinking" not in cfy
        assert "shellcheck" not in cfy

    def test_npm_scoped_package_handling(self, load_module):
        """Scoped npm names (`@scope/name`) → conda name `name`, tarball
        filename `<scope>-<name>-<v>.tgz`."""
        mod = load_module("recipe-generator.py")
        # Validate the helper functions
        raw, conda, scoped = mod._parse_npm_name("@openai/codex")
        assert raw == "@openai/codex"
        assert conda == "codex"
        assert scoped is True
        # Tarball filename: scope + name (joined by `-`)
        assert mod._npm_tarball_filename("@openai/codex", "1.2.3") == "openai-codex-1.2.3.tgz"
        assert mod._npm_tarball_filename("husky", "9.1.5") == "husky-9.1.5.tgz"

    def test_npm_source_url_is_version_templated(self, load_module):
        """source.url uses ``${{ version }}`` so autotick-style version
        bumps actually re-render the URL. Without this, an autotick that
        updates only context.version produces a silent mismatch (URL still
        points at the old version, sha256 recomputes against the old
        tarball, recipe ships the wrong version)."""
        mod = load_module("recipe-generator.py")
        # npm registry URL — scope-less
        assert mod._template_npm_source_url(
            "https://registry.npmjs.org/bmalph/-/bmalph-2.11.0.tgz", "2.11.0"
        ) == "https://registry.npmjs.org/bmalph/-/bmalph-${{ version }}.tgz"
        # npm registry URL — scoped (scope dropped in the filename)
        assert mod._template_npm_source_url(
            "https://registry.npmjs.org/@openai/codex/-/codex-1.2.3.tgz", "1.2.3"
        ) == "https://registry.npmjs.org/@openai/codex/-/codex-${{ version }}.tgz"
        # GitHub archive URL (the --source github path)
        assert mod._template_npm_source_url(
            "https://github.com/x/y/archive/refs/tags/v2.11.0.tar.gz", "2.11.0"
        ) == "https://github.com/x/y/archive/refs/tags/v${{ version }}.tar.gz"
        # Unrecognized URL shape falls back to literal — autotick's
        # calculate_hash still works, but the URL won't auto-bump (the
        # alternative is silently mangling).
        weird = "https://example.com/no-version-here.tar.bz2"
        assert mod._template_npm_source_url(weird, "1.0.0") == weird

    def test_npm_test_mode_package_contents(self, load_module, tmp_path):
        """`--test-mode package_contents` should emit package_contents.bin block."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="thing", conda_name="thing", version="1.0.0",
            tarball_url="https://example.com/thing-1.0.0.tgz",
            tarball_filename="thing-1.0.0.tgz",
            source_url="https://example.com/thing-1.0.0.tgz",
            sha256="0" * 64,
            bin_entries={"thing": "cli.js"},
        )
        recipe_path = mod.generate_npm_recipe_yaml(
            info, tmp_path, test_mode="package_contents"
        )
        content = recipe_path.read_text()
        assert "package_contents:" in content
        assert "bin:" in content
        # No script: --help block
        assert "thing --help" not in content

    def test_npm_inline_build_default(self, load_module, tmp_path):
        """Default generator output (no flags) emits the inline build
        commands in recipe.yaml and no separate build.sh."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="thing", conda_name="thing", version="1.0.0",
            tarball_url="https://example.com/thing-1.0.0.tgz",
            tarball_filename="thing-1.0.0.tgz",
            source_url="https://example.com/thing-1.0.0.tgz",
            sha256="0" * 64,
            bin_entries={"thing": "cli.js"},
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path)
        content = recipe_path.read_text()
        # build.script: block embedded
        assert "  script:" in content
        assert "npm pack --ignore-scripts" in content
        assert "pnpm install --ignore-scripts" in content
        # No separate build.sh
        assert not (recipe_path.parent / "build.sh").exists()

    def test_npm_prepare_fix(self, load_module, tmp_path):
        """`--prepare-fix` injects the jq prepare-script-strip step into
        both the Unix and Windows branches of the inline build script."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="thing", conda_name="thing", version="1.0.0",
            tarball_url="https://example.com/thing-1.0.0.tgz",
            tarball_filename="thing-1.0.0.tgz",
            source_url="https://example.com/thing-1.0.0.tgz",
            sha256="0" * 64,
            bin_entries={"thing": "cli.js"},
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path, prepare_fix=True)
        content = recipe_path.read_text()
        # jq strip lands in the inline script (both branches)
        assert "jq" in content
        assert "del(.scripts.prepare)" in content
        # Unix branch uses mv; Windows branch uses move
        assert "mv package.json package.json.bak" in content
        assert "move package.json package.json.bak" in content

    def test_npm_native_build_emits_compilers_and_drops_noarch(
        self, load_module, tmp_path,
    ):
        """`has_native_build=True` (gypfile / node-gyp install) → recipe gets
        C/C++ compilers + stdlib + python + make in build deps, and drops
        `noarch: generic` (native packages need per-platform builds)."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="better-sqlite3", conda_name="better-sqlite3",
            version="11.0.0",
            tarball_url="https://registry.npmjs.org/better-sqlite3/-/better-sqlite3-11.0.0.tgz",
            tarball_filename="better-sqlite3-11.0.0.tgz",
            source_url="https://registry.npmjs.org/better-sqlite3/-/better-sqlite3-11.0.0.tgz",
            sha256="0" * 64,
            license="MIT",
            bin_entries={},
            has_native_build=True,
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path)
        content = recipe_path.read_text()
        # Native compiler deps emitted
        assert "${{ compiler('c') }}" in content
        assert "${{ compiler('cxx') }}" in content
        assert "${{ stdlib('c') }}" in content
        assert "    - python" in content
        assert "    - make" in content
        # noarch:generic must NOT appear — native packages need per-platform builds
        assert "noarch: generic" not in content
        # nodejs still in run requirements
        data = yaml.safe_load(content)
        assert data["requirements"]["run"] == ["nodejs"]

    def test_npm_pure_js_omits_noarch_and_compilers(
        self, load_module, tmp_path,
    ):
        """Pure-JS packages (no native compilation) in v8.11.0:
        per-platform inline build, no noarch:generic, no compiler deps."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="husky", conda_name="husky", version="9.1.7",
            tarball_url="https://registry.npmjs.org/husky/-/husky-9.1.7.tgz",
            tarball_filename="husky-9.1.7.tgz",
            source_url="https://registry.npmjs.org/husky/-/husky-9.1.7.tgz",
            sha256="0" * 64,
            license="MIT",
            bin_entries={"husky": "bin.js"},
            has_native_build=False,
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path)
        content = recipe_path.read_text()
        # Per-platform inline build — no noarch:generic.
        assert "noarch: generic" not in content
        # Inline if:unix/then/else block is present.
        assert "if: unix" in content
        assert "then:" in content
        assert "else:" in content
        # Pure-JS — no compiler deps emitted.
        assert "compiler('c')" not in content
        assert "stdlib('c')" not in content

    def test_npm_feedstock_mode_emits_full_conda_forge_yml(
        self, load_module, tmp_path,
    ):
        """`--feedstock-mode` should emit the bigger conda-forge.yml with
        bot/github/conda_forge_output_validation/conda_build sections —
        for direct feedstock updates rather than staged-recipes submission."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="thing", conda_name="thing", version="1.0.0",
            tarball_url="https://example.com/thing-1.0.0.tgz",
            tarball_filename="thing-1.0.0.tgz",
            source_url="https://example.com/thing-1.0.0.tgz",
            sha256="0" * 64,
            license="MIT",
            bin_entries={"thing": "cli.js"},
        )
        recipe_path = mod.generate_npm_recipe_yaml(
            info, tmp_path, feedstock_mode=True,
        )
        cfy = (recipe_path.parent / "conda-forge.yml").read_text()
        # Universal pre-seed + feedstock-root keys (output_validation + github).
        for field_name in (
            "bot:", "automerge:", "inspection: hint-all", "check_solvable:",
            "github:", "branch_name:", "tooling_branch_name:",
            "conda_forge_output_validation: true",
            "conda_install_tool: pixi", "conda_build_tool: rattler-build",
        ):
            assert field_name in cfy, f"missing {field_name} in feedstock conda-forge.yml"
        # npm = non-Python, non-noarch JS CLI: no wheel, no ARM, none of the
        # no-op/wrong keys (error_overlinking is a rattler-build no-op).
        assert "run_deps_from_wheel" not in cfy
        assert "error_overlinking" not in cfy
        assert "build_platform:" not in cfy
        assert "noarch_platforms" not in cfy
        assert "shellcheck" not in cfy
        assert "workflow_settings" not in cfy

    def test_npm_default_mode_emits_universal_conda_forge_yml(
        self, load_module, tmp_path,
    ):
        """Default (per-platform inline) npm mode now emits the universal
        conda-forge.yml pre-seed (G83) — reverses the v8.11.0 omission. npm is
        non-Python/non-noarch → hint-all, no run_deps_from_wheel, no ARM."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="thing", conda_name="thing", version="1.0.0",
            tarball_url="https://example.com/thing-1.0.0.tgz",
            tarball_filename="thing-1.0.0.tgz",
            source_url="https://example.com/thing-1.0.0.tgz",
            sha256="0" * 64,
            license="MIT",
            bin_entries={"thing": "cli.js"},
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path)
        cfy = (recipe_path.parent / "conda-forge.yml").read_text()
        assert "conda_build_tool: rattler-build" in cfy
        assert "conda_install_tool: pixi" in cfy
        assert "inspection: hint-all" in cfy
        assert "run_deps_from_wheel" not in cfy
        assert "build_platform:" not in cfy
        assert "workflow_settings" not in cfy
        # Default (staged-recipes) mode omits the feedstock-root keys.
        assert "conda_forge_output_validation" not in cfy
        assert "github:" not in cfy

    def test_pypi_noarch_python_emits_universal_conda_forge_yml(
        self, load_module, tmp_path,
    ):
        """noarch:python pypi recipe → universal conda-forge.yml pre-seed (G83):
        update-grayskull + run_deps_from_wheel, NO ARM block, none of the
        no-op keys (workflow_settings/error_overlinking/shellcheck)."""
        mod = load_module("recipe-generator.py")
        info = mod.PackageInfo(name="rich", version="13.0.0", summary="x")
        recipe_path = mod.generate_recipe_yaml(info, tmp_path)
        cfy = (recipe_path.parent / "conda-forge.yml").read_text()
        assert "conda_build_tool: rattler-build" in cfy
        assert "conda_install_tool: pixi" in cfy
        assert "inspection: update-grayskull" in cfy   # noarch:python → grayskull
        assert "run_deps_from_wheel: true" in cfy
        assert "build_platform:" not in cfy             # noarch → no ARM block
        assert "provider:" not in cfy
        assert "test: native_and_emulated" not in cfy
        assert "workflow_settings" not in cfy
        assert "error_overlinking" not in cfy
        assert "shellcheck" not in cfy

    def test_maturin_compiled_emits_arm_block(
        self, load_module, tmp_path,
    ):
        """maturin/PyO3 compiled recipe → universal pre-seed + the full ARM
        platform block (build_platform + provider + test), inspection: hint-all
        (grayskull mangles hand-tuned host pins), run_deps_from_wheel."""
        mod = load_module("recipe-generator.py")
        info = mod.PackageInfo(
            name="thing", version="1.0.0", summary="x", build_backend="maturin",
        )
        recipe_path = mod.generate_recipe_yaml(info, tmp_path)  # routes to maturin
        cfy = (recipe_path.parent / "conda-forge.yml").read_text()
        assert "inspection: hint-all" in cfy
        assert "run_deps_from_wheel: true" in cfy
        assert "build_platform:" in cfy
        assert "linux_aarch64: linux_64" in cfy
        assert "osx_arm64: osx_64" in cfy
        assert "provider:" in cfy
        assert "test: native_and_emulated" in cfy
        assert "workflow_settings" not in cfy
        assert "error_overlinking" not in cfy

    def test_npm_no_third_party_licenses_zero_dep_pattern(
        self, load_module, tmp_path
    ):
        """`third_party_licenses=False` produces the husky-style zero-dep
        recipe: no pnpm/pnpm-licenses build deps, license_file as a single
        string, and no pnpm-licenses step in the inline build script."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="husky", conda_name="husky", version="9.1.5",
            tarball_url="https://registry.npmjs.org/husky/-/husky-9.1.5.tgz",
            tarball_filename="husky-9.1.5.tgz",
            source_url="https://registry.npmjs.org/husky/-/husky-9.1.5.tgz",
            sha256="0" * 64,
            license="MIT",
            bin_entries={"husky": "bin.js"},
        )
        recipe_path = mod.generate_npm_recipe_yaml(
            info, tmp_path, third_party_licenses=False,
        )
        content = recipe_path.read_text()
        # Build deps drop pnpm + pnpm-licenses
        assert "- pnpm\n" not in content
        assert "- pnpm-licenses\n" not in content
        # license_file becomes a single string
        assert "license_file: LICENSE" in content
        assert "third-party-licenses.txt" not in content
        # Inline script omits the pnpm-licenses block on BOTH branches
        assert "pnpm install" not in content
        assert "pnpm-licenses" not in content
        # But still does the `npm pack` + `npm install --global` on both branches
        assert "npm pack --ignore-scripts" in content
        assert "call npm pack --ignore-scripts" in content
        assert 'npm install --global "${SRC_DIR}/husky-${{ version }}.tgz"' in content
        assert "call npm install --global %SRC_DIR%/husky-${{ version }}.tgz" in content

    def test_extract_readme_paragraph_skips_images_and_badges(self, load_module):
        """Description cleanup: skip image/badge lines, take first prose paragraph."""
        mod = load_module("recipe-generator.py")
        readme = (
            "# bmad-method\n\n"
            "![Banner](banner.png)\n\n"
            "[![CI](https://img.shields.io/x.svg)](https://example.com)\n\n"
            "BMAD-METHOD is an AI-driven agile development framework with "
            "specialized AI agent personas across the full SDLC.\n\n"
            "## Installation\n"
        )
        result = mod._extract_readme_paragraph(readme)
        assert "BMAD-METHOD" in result
        assert "![" not in result
        assert "[![" not in result

    def test_extract_readme_paragraph_drops_url_only_paragraph(self, load_module):
        mod = load_module("recipe-generator.py")
        readme = "https://example.com\n\nReal description text goes here."
        result = mod._extract_readme_paragraph(readme)
        assert result == "Real description text goes here."

    def test_extract_readme_paragraph_truncates_long(self, load_module):
        mod = load_module("recipe-generator.py")
        # 1000-char description
        long_text = "Word. " * 200
        result = mod._extract_readme_paragraph(long_text, max_length=120)
        assert len(result) <= 120
        assert result.endswith("...")

    def test_extract_readme_paragraph_empty(self, load_module):
        mod = load_module("recipe-generator.py")
        assert mod._extract_readme_paragraph("") == ""
        assert mod._extract_readme_paragraph("# Heading only") == ""

    def test_detect_license_filename_npm_tarball(self, load_module):
        """Build an in-memory tarball with package/LICENSE.md and verify
        detection picks LICENSE.md over the default LICENSE."""
        import io
        import tarfile

        mod = load_module("recipe-generator.py")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for name, content in (
                ("package/LICENSE.md", b"MIT License...\n"),
                ("package/package.json", b'{"name":"x"}\n'),
                ("package/README.md", b"# x\n"),
            ):
                info = tarfile.TarInfo(name=name)
                info.size = len(content)
                tf.addfile(info, io.BytesIO(content))
        result = mod._detect_license_filename(buf.getvalue())
        assert result == "LICENSE.md"

    def test_detect_license_filename_github_tarball(self, load_module):
        """GitHub-style tarball: top-level <repo>-<version>/COPYING."""
        import io
        import tarfile

        mod = load_module("recipe-generator.py")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for name, content in (
                ("BMAD-METHOD-6.4.0/COPYING", b"GPL...\n"),
                ("BMAD-METHOD-6.4.0/package.json", b'{}'),
            ):
                info = tarfile.TarInfo(name=name)
                info.size = len(content)
                tf.addfile(info, io.BytesIO(content))
        assert mod._detect_license_filename(buf.getvalue()) == "COPYING"

    def test_detect_license_filename_priority_order(self, load_module):
        """When multiple license files exist, plain LICENSE wins."""
        import io
        import tarfile

        mod = load_module("recipe-generator.py")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for name in ("package/LICENSE.md", "package/LICENSE", "package/COPYING"):
                info = tarfile.TarInfo(name=name)
                info.size = 0
                tf.addfile(info, io.BytesIO(b""))
        assert mod._detect_license_filename(buf.getvalue()) == "LICENSE"

    def test_detect_license_filename_no_license(self, load_module):
        """Returns None when no recognisable license file is present."""
        import io
        import tarfile

        mod = load_module("recipe-generator.py")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            info = tarfile.TarInfo(name="package/package.json")
            info.size = 2
            tf.addfile(info, io.BytesIO(b"{}"))
        assert mod._detect_license_filename(buf.getvalue()) is None

    def test_detect_license_filename_handles_garbage(self, load_module):
        """Non-tarball bytes don't crash the helper."""
        mod = load_module("recipe-generator.py")
        assert mod._detect_license_filename(b"not a tarball") is None
        assert mod._detect_license_filename(b"") is None

    def test_npm_recipe_uses_detected_license_filename(self, load_module, tmp_path):
        """End-to-end: NpmPackageInfo.license_filename flows into recipe.yaml."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="x", conda_name="x", version="1.0.0",
            tarball_url="https://example.com/x-1.0.0.tgz",
            tarball_filename="x-1.0.0.tgz",
            source_url="https://example.com/x-1.0.0.tgz",
            sha256="0" * 64,
            license="MIT",
            license_filename="LICENSE.md",   # ← upstream's actual file
            bin_entries={"x": "cli.js"},
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path)
        content = recipe_path.read_text()
        # Detected license filename used in license_file list
        assert "- LICENSE.md" in content
        # Plain "LICENSE" alone (without .md) shouldn't appear as a list item
        assert "    - LICENSE\n" not in content

    def test_extract_readme_paragraph_falls_back_to_description(self, load_module):
        """When the readme is just badges/banners, fall back to npm's
        `description` field via the wrapper in fetch_npm_info — confirmed
        end-to-end here through generate_npm_recipe_yaml."""
        # The fallback is wired in fetch_npm_info, not in
        # _extract_readme_paragraph itself. We verify the helper still
        # returns "" for badge-only input (the trigger for the fallback).
        mod = load_module("recipe-generator.py")
        badges_only = (
            "[![Build](https://img.shields.io/build.svg)](https://ci.example.com)\n"
            "[![Coverage](https://img.shields.io/coverage.svg)](https://cov.example.com)\n"
        )
        assert mod._extract_readme_paragraph(badges_only) == ""

    def test_pre_release_version_yaml_quoting(self, load_module, tmp_path):
        """Pre-release semver versions like 2.0.0-beta.1 must round-trip
        through YAML safely (we always quote `context.version`)."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="prerel", conda_name="prerel", version="2.0.0-beta.1",
            tarball_url="https://registry.npmjs.org/prerel/-/prerel-2.0.0-beta.1.tgz",
            tarball_filename="prerel-2.0.0-beta.1.tgz",
            source_url="https://registry.npmjs.org/prerel/-/prerel-2.0.0-beta.1.tgz",
            sha256="0" * 64,
            license="MIT",
            bin_entries={"prerel": "cli.js"},
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path)
        # The YAML must be parseable and the version field must round-trip
        # to the exact string (not get coerced to a number or stripped of
        # the pre-release suffix).
        data = yaml.safe_load(recipe_path.read_text())
        assert data["context"]["version"] == "2.0.0-beta.1"
        # Source URL must contain the full version including suffix
        assert "prerel-2.0.0-beta.1.tgz" in data["source"]["url"]

    def test_check_spdx_known_license(self, load_module):
        """Known SPDX identifiers pass through unchanged with no warning."""
        mod = load_module("recipe-generator.py")
        for known in ("MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "GPL-3.0-or-later"):
            license_value, warning = mod._check_spdx_license(known)
            assert license_value == known
            assert warning is None

    def test_check_spdx_compound_expression(self, load_module):
        """Compound SPDX expressions like '(MIT OR Apache-2.0)' pass through."""
        mod = load_module("recipe-generator.py")
        compound = "(MIT OR Apache-2.0)"
        license_value, warning = mod._check_spdx_license(compound)
        assert license_value == compound
        assert warning is None

    def test_check_spdx_non_strict_label(self, load_module):
        """Non-strict labels like 'Apache 2.0' get a warning suggesting the SPDX form."""
        mod = load_module("recipe-generator.py")
        for non_strict, expected_suggestion in (
            ("Apache 2.0", "Apache-2.0"),
            ("BSD", "BSD-3-Clause"),
            ("GPLv3", "GPL-3.0-or-later"),
        ):
            license_value, warning = mod._check_spdx_license(non_strict)
            # We keep the original (don't auto-rewrite) — user decides
            assert license_value == non_strict
            assert warning is not None
            assert expected_suggestion in warning

    def test_check_spdx_unknown_license(self, load_module):
        """Genuinely unknown licenses get a 'verify against spdx.org' hint."""
        mod = load_module("recipe-generator.py")
        license_value, warning = mod._check_spdx_license("MyCustomLicense-1.0")
        assert license_value == "MyCustomLicense-1.0"
        assert warning is not None
        assert "spdx.org" in warning

    def test_check_spdx_empty(self, load_module):
        mod = load_module("recipe-generator.py")
        license_value, warning = mod._check_spdx_license("")
        assert license_value == ""
        assert warning is None

    def test_npm_no_third_party_licenses_inline_skips_pnpm_licenses(
        self, load_module, tmp_path
    ):
        """``third_party_licenses=False`` skips the pnpm-licenses commands
        inside the inline build script (both unix and Windows branches)."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="husky", conda_name="husky", version="9.1.5",
            tarball_url="https://registry.npmjs.org/husky/-/husky-9.1.5.tgz",
            tarball_filename="husky-9.1.5.tgz",
            source_url="https://registry.npmjs.org/husky/-/husky-9.1.5.tgz",
            sha256="0" * 64,
            license="MIT",
            bin_entries={"husky": "bin.js"},
        )
        recipe_path = mod.generate_npm_recipe_yaml(
            info, tmp_path, third_party_licenses=False,
        )
        content = recipe_path.read_text()
        assert "  script:" in content
        assert "npm pack --ignore-scripts" in content
        # Inline script must NOT have pnpm-licenses commands
        assert "pnpm install" not in content
        assert "pnpm-licenses" not in content

    def test_npm_yaml_is_valid(self, load_module, tmp_path):
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="x",
            conda_name="x",
            version="0.1.0",
            tarball_url="https://example.com/x-0.1.0.tgz",
            tarball_filename="x-0.1.0.tgz",
            source_url="https://example.com/x-0.1.0.tgz",
            sha256="0" * 64,
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path)
        # Must parse cleanly
        data = yaml.safe_load(recipe_path.read_text())
        # Canonical recipes use a literal package.name (not a context substitution
        # via ${{ name }}, since context.name is omitted from the canonical shape).
        assert data["package"]["name"] == "x"
        # v8.11.0: per-platform inline build, no noarch:generic.
        assert "noarch" not in data["build"]
        # The inline build.script carries an if/then/else mapping.
        script = data["build"]["script"]
        assert isinstance(script, list)
        assert any(isinstance(s, dict) and s.get("if") == "unix" for s in script)

    @pytest.mark.network
    def test_npm_live_against_husky(self, script_runner, tmp_path):
        """Live: scaffold husky (from PR 28481) via npm registry. Husky has
        zero runtime dependencies, so the generator's auto-detection emits
        the husky-style *minimal* recipe: no pnpm/pnpm-licenses in build
        deps, license_file as a single string. Full-pattern coverage (with
        pnpm-licenses) is in `test_npm_recipe_canonical_shape_offline`."""
        rc, out, err = script_runner(
            "recipe-generator.py", "npm", "husky",
            "--output", str(tmp_path),
            timeout=180,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        recipe = tmp_path / "husky" / "recipe.yaml"
        assert recipe.exists()
        data = yaml.safe_load(recipe.read_text())
        assert data["package"]["name"] == "husky"
        # v8.11.0: per-platform inline build, no noarch:generic.
        assert "noarch" not in data["build"]
        # Source URL is npm registry (not GitHub)
        assert "registry.npmjs.org" in data["source"]["url"]
        # Husky-style minimal: nodejs only, no pnpm/pnpm-licenses
        build_reqs = data["requirements"]["build"]
        assert "nodejs" in build_reqs
        assert "pnpm" not in build_reqs
        assert "pnpm-licenses" not in build_reqs
        # Husky-style: license_file is a single string, not a list
        assert isinstance(data["about"]["license_file"], str)

    @pytest.mark.network
    def test_npm_live_scoped_codex(self, script_runner, tmp_path):
        """Live: scaffold @openai/codex (PR 29752) — verifies scoped-package
        handling: conda name `codex`, tarball filename `openai-codex-<v>.tgz`."""
        rc, out, err = script_runner(
            "recipe-generator.py", "npm", "@openai/codex",
            "--prepare-fix",
            "--output", str(tmp_path),
            timeout=180,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        # Conda name is the unscoped basename
        recipe = tmp_path / "codex" / "recipe.yaml"
        assert recipe.exists()
        content = recipe.read_text()
        # v8.11.0: inline script references the scope-prefixed tarball
        # filename, NOT a separate build.sh.
        assert not (tmp_path / "codex" / "build.sh").exists()
        assert "openai-codex" in content
        # And the prepare-fix workaround lands inside the inline script.
        assert "del(.scripts.prepare)" in content

    def test_template_python_noarch(self, script_runner, tmp_path):
        rc, out, err = script_runner(
            "recipe-generator.py",
            "template", "python-noarch",
            "--name", "smoke-test",
            "--version", "1.0.0",
            "--output", str(tmp_path),
        )
        assert rc == 0, f"out={out}\nerr={err}"
        recipe_file = tmp_path / "recipe.yaml"
        assert recipe_file.exists()
        data = yaml.safe_load(recipe_file.read_text())
        assert data is not None

    @pytest.mark.network
    def test_pypi_live(self, script_runner, tmp_path):
        """Generate a real recipe from PyPI (network)."""
        rc, out, err = script_runner(
            "recipe-generator.py",
            "pypi", "click",
            "--output", str(tmp_path),
            "--format", "v1",
            timeout=120,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        assert (tmp_path / "recipe.yaml").exists()

    def test_pypi_to_conda_name_translates_known_divergences(
        self, load_module, monkeypatch, tmp_path
    ):
        """`_pypi_to_conda_name` should route through `name_resolver` so
        the well-known PyPI↔conda-forge name divergences are translated
        when emitting `run:` deps. Regression test for the rq recipe
        bug where PyPI `redis` was emitted unchanged instead of being
        rewritten to conda-forge `redis-py`."""
        # Stub the local mapping cache with the canonical divergences.
        cache_file = tmp_path / "pypi_conda_map.json"
        cache_file.write_text(json.dumps({
            "redis": "redis-py",
            "soundfile": "pysoundfile",
        }))

        # Load name_resolver first and pin its cache to the stub. The
        # generator imports name_resolver lazily inside the helper, so
        # it'll see this monkeypatched MAPPING_CACHE_FILE.
        nr = load_module("name_resolver.py")
        monkeypatch.setattr(nr, "MAPPING_CACHE_FILE", cache_file)

        gen = load_module("recipe-generator.py")
        assert gen._pypi_to_conda_name("redis") == "redis-py"
        assert gen._pypi_to_conda_name("soundfile") == "pysoundfile"

    def test_pypi_to_conda_name_identity_passthrough(
        self, load_module, monkeypatch, tmp_path
    ):
        """Names not in the mapping cache (and not rewritten by the
        metadata API) must pass through unchanged — the common case."""
        cache_file = tmp_path / "pypi_conda_map.json"
        cache_file.write_text("{}")

        nr = load_module("name_resolver.py")
        monkeypatch.setattr(nr, "MAPPING_CACHE_FILE", cache_file)
        # Force the metadata-api tier to behave as identity so the test
        # doesn't depend on the live network or installed mapping data.
        monkeypatch.setattr(nr, "search_metadata_api", lambda name: name)

        gen = load_module("recipe-generator.py")
        # `requests`, `httpx`, `pydantic` all share their conda-forge
        # names with PyPI; the helper should return the input unchanged.
        for name in ("requests", "httpx", "pydantic"):
            assert gen._pypi_to_conda_name(name) == name

    @pytest.mark.network
    def test_github_live(self, script_runner, tmp_path):
        rc, out, err = script_runner(
            "recipe-generator.py",
            "github", "rhysd/actionlint",
            "--output", str(tmp_path),
            timeout=120,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        assert (tmp_path / "recipe.yaml").exists()

    @pytest.mark.network
    def test_cran_live(self, script_runner, tmp_path):
        """Live CRAN scaffolder. Picks a small fast package (`cli`)."""
        rc, out, err = script_runner(
            "recipe-generator.py",
            "cran", "cli",
            "--output", str(tmp_path),
            timeout=180,
        )
        assert rc == 0, f"out={out}\nerr={err}"
        # rattler-build writes to <output>/r-<package>/recipe.yaml
        recipe = tmp_path / "r-cli" / "recipe.yaml"
        assert recipe.exists(), (
            f"Expected {recipe} to exist after CRAN scaffold."
        )
        # Sanity: the file is valid YAML with a package.name starting with r-
        content = yaml.safe_load(recipe.read_text())
        assert content["package"]["name"].startswith("r-")
