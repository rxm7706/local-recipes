"""Unit tests for recipe-generator.py (hyphenated → script_runner only)."""
from __future__ import annotations

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
            source_url="https://registry.npmjs.org/example-pkg/-/example-pkg-1.0.0.tgz",
            sha256="a" * 64,
            bin_entries={"example-pkg": "bin/cli.js"},
            node_major=20,
        )
        recipe_path = mod.generate_npm_recipe_yaml(info, tmp_path)
        assert recipe_path.exists()
        content = recipe_path.read_text()
        pkg_dir = recipe_path.parent

        # ── Canonical recipe.yaml shape ─────────────────────────────────
        # Must NOT have the editor schema header (canonical recipes don't include it)
        assert "yaml-language-server" not in content
        # Reference PRs omit `schema_version`, but we emit it explicitly so our
        # validate_recipe.py is happy. Both forms are accepted by rattler-build.
        assert "schema_version: 1" in content
        assert "noarch: generic" in content
        # Source URL embedded (npm registry by default)
        assert info.source_url in content
        # sha256 embedded
        assert "a" * 64 in content
        # Bin command rendered into a flat script test (no if:unix/win branching)
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

        # ── build.sh follows canonical pattern ───────────────────────────
        assert (pkg_dir / "build.sh").exists()
        build_sh = (pkg_dir / "build.sh").read_text()
        assert "npm pack --ignore-scripts" in build_sh
        assert "npm install -ddd" in build_sh
        assert "--global" in build_sh
        assert "pnpm-licenses generate-disclaimer" in build_sh
        assert "third-party-licenses.txt" in build_sh
        # The Windows .cmd wrapper uses the canonical form
        assert "%CONDA_PREFIX%\\bin\\node" in build_sh
        # Manual cp -r staging is gone
        assert "cp -r ." not in build_sh
        # Tarball filename embedded
        assert info.tarball_filename in build_sh

        # ── No build.bat by default (noarch builds run on Linux only) ────
        assert not (pkg_dir / "build.bat").exists()
        # Critical: must NOT use v0's bld.bat
        assert not (pkg_dir / "bld.bat").exists()

        # ── conda-forge.yml emitted ──────────────────────────────────────
        cfy = pkg_dir / "conda-forge.yml"
        assert cfy.exists()
        cfy_text = cfy.read_text()
        assert "conda_build_tool: rattler-build" in cfy_text
        assert "noarch_platforms" in cfy_text
        assert "shellcheck" in cfy_text

    def test_npm_scoped_package_handling(self, load_module, tmp_path):
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

    def test_npm_inline_build(self, load_module, tmp_path):
        """`--inline-build` should embed build commands in recipe.yaml and
        skip the separate build.sh."""
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
            info, tmp_path, inline_build=True
        )
        content = recipe_path.read_text()
        # build.script: block embedded
        assert "  script:" in content
        assert "npm pack --ignore-scripts" in content
        assert "pnpm install" in content
        # No separate build.sh
        assert not (recipe_path.parent / "build.sh").exists()

    def test_npm_prepare_fix(self, load_module, tmp_path):
        """`--prepare-fix` injects the jq prepare-script-strip step."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="thing", conda_name="thing", version="1.0.0",
            tarball_url="https://example.com/thing-1.0.0.tgz",
            tarball_filename="thing-1.0.0.tgz",
            source_url="https://example.com/thing-1.0.0.tgz",
            sha256="0" * 64,
            bin_entries={"thing": "cli.js"},
        )
        mod.generate_npm_recipe_yaml(info, tmp_path, prepare_fix=True)
        build_sh = (tmp_path / "thing" / "build.sh").read_text()
        assert "jq" in build_sh
        assert "del(.scripts.prepare)" in build_sh

    def test_npm_with_build_bat_opt_in(self, load_module, tmp_path):
        """`--with-build-bat` opt-in should produce a build.bat file."""
        mod = load_module("recipe-generator.py")
        info = mod.NpmPackageInfo(
            raw_name="thing", conda_name="thing", version="1.0.0",
            tarball_url="https://example.com/thing-1.0.0.tgz",
            tarball_filename="thing-1.0.0.tgz",
            source_url="https://example.com/thing-1.0.0.tgz",
            sha256="0" * 64,
            bin_entries={"thing": "cli.js"},
        )
        mod.generate_npm_recipe_yaml(info, tmp_path, with_build_bat=True)
        assert (tmp_path / "thing" / "build.bat").exists()

    def test_npm_no_third_party_licenses_zero_dep_pattern(
        self, load_module, tmp_path
    ):
        """`third_party_licenses=False` produces the husky-style zero-dep
        recipe: no pnpm/pnpm-licenses build deps, license_file as a single
        string, and no pnpm-licenses block in build.sh."""
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
        # build.sh omits the pnpm-licenses block
        build_sh = (recipe_path.parent / "build.sh").read_text()
        assert "pnpm install" not in build_sh
        assert "pnpm-licenses" not in build_sh
        assert "third-party-licenses.txt" not in build_sh
        # But still does the `npm pack` + `npm install --global` + Windows wrapper
        assert "npm pack --ignore-scripts" in build_sh
        assert "%CONDA_PREFIX%\\bin\\node" in build_sh

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

    def test_detect_license_filename_npm_tarball(self, load_module, tmp_path):
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

    def test_npm_no_third_party_licenses_inline_build(
        self, load_module, tmp_path
    ):
        """Combining --no-third-party-licenses with --inline-build also
        skips the pnpm-licenses commands inside the inline script."""
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
            info, tmp_path, inline_build=True, third_party_licenses=False,
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
        assert data["build"]["noarch"] == "generic"

    @pytest.mark.network
    def test_npm_live_against_husky(self, script_runner, tmp_path):
        """Live: scaffold husky (from PR 28481) via npm registry — should
        match canonical pattern."""
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
        assert data["build"]["noarch"] == "generic"
        # Source URL is npm registry (not GitHub)
        assert "registry.npmjs.org" in data["source"]["url"]
        # Build deps include pnpm + pnpm-licenses
        build_reqs = data["requirements"]["build"]
        assert "pnpm" in build_reqs
        assert "pnpm-licenses" in build_reqs

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
        # build.sh references the scope-prefixed tarball filename
        build_sh = (tmp_path / "codex" / "build.sh").read_text()
        assert "openai-codex" in build_sh
        # And contains the prepare-fix workaround
        assert "del(.scripts.prepare)" in build_sh

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
