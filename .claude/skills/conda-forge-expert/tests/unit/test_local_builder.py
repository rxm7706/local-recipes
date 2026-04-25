"""Unit tests for local_builder.py — Docker-less cross-platform builder."""
from __future__ import annotations

import json
import os
from unittest import mock


COMPILED_RECIPE_YAML = """\
schema_version: 1
context:
  version: "1.0.0"
package:
  name: example-compiled
  version: ${{ version }}
source:
  url: https://example.com/x-1.0.0.tar.gz
  sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
build:
  number: 0
  script: cargo build --release
requirements:
  build:
    - ${{ compiler('c') }}
    - ${{ stdlib('c') }}
about:
  license: MIT
  license_file: LICENSE
  summary: compiled fixture
"""


NOARCH_RECIPE_YAML = """\
schema_version: 1
context:
  version: "1.0.0"
package:
  name: example-noarch
  version: ${{ version }}
source:
  url: https://example.com/x-1.0.0.tgz
  sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
build:
  number: 0
  noarch: generic
requirements:
  build:
    - nodejs
about:
  license: MIT
  license_file: LICENSE
  summary: noarch fixture
"""


class TestLocalBuilder:
    def test_help(self, script_runner):
        rc, out, _ = script_runner("local_builder.py", "--help")
        assert rc == 0
        for flag in ("--platform", "--all-platforms", "--dry-run", "--check"):
            assert flag in out, f"missing {flag} in --help"

    def test_check_diagnostic(self, script_runner):
        """`--check` prints a structured environment report."""
        rc, out, _ = script_runner("local_builder.py", "--check")
        assert rc == 0
        report = json.loads(out)
        for key in (
            "host_system", "host_machine", "native_platform",
            "rattler_build_path", "platform_support",
        ):
            assert key in report
        # All 5 platforms surfaced
        for plat in ("linux-64", "linux-aarch64", "osx-64", "osx-arm64", "win-64"):
            assert plat in report["platform_support"]

    def test_detect_native_platform_returns_known_value(self, load_module):
        mod = load_module("local_builder.py")
        native = mod.detect_native_platform()
        assert native in mod.ALL_PLATFORMS

    def test_build_command_native_linux64(self, load_module, tmp_path):
        """Native linux-64 build runs WITH tests (no --no-test)."""
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        cmd = mod._build_command(recipe, "linux-64", is_native=True)
        assert "rattler-build" in cmd[0]
        assert "build" in cmd
        assert "--target-platform" in cmd
        assert "linux-64" in cmd
        # Channel info comes either via -c (no variant config) or via -m
        # variant config's channel_sources field. The project's
        # .ci_support/linux64.yaml has channel_sources, so -m wins.
        assert ("-c" in cmd and "conda-forge" in cmd) or "-m" in cmd
        # Native → no --no-test, no --env-isolation override
        assert "--no-test" not in cmd
        assert "--env-isolation" not in cmd

    def test_build_command_cross_aarch64(self, load_module, tmp_path):
        """linux-aarch64 cross-build adds --no-test."""
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        cmd = mod._build_command(recipe, "linux-aarch64", is_native=False)
        assert "--target-platform" in cmd and "linux-aarch64" in cmd
        assert "--no-test" in cmd
        assert "--allow-symlinks-on-windows" not in cmd

    def test_build_command_cross_osx_arm64(self, load_module, tmp_path):
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        cmd = mod._build_command(recipe, "osx-arm64", is_native=False)
        assert "osx-arm64" in cmd
        assert "--no-test" in cmd
        # osx-* should NOT have the windows symlink flag
        assert "--allow-symlinks-on-windows" not in cmd

    def test_build_command_cross_win64_adds_symlink_flag(
        self, load_module, tmp_path,
    ):
        """win-64 cross-build adds --allow-symlinks-on-windows."""
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        cmd = mod._build_command(recipe, "win-64", is_native=False)
        assert "--target-platform" in cmd and "win-64" in cmd
        assert "--no-test" in cmd
        assert "--allow-symlinks-on-windows" in cmd

    def test_build_command_multiple_channels(self, load_module, tmp_path):
        """When no variant config provides channel_sources, multiple -c
        channel flags are emitted."""
        from unittest import mock as _mock

        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        # Mock out variant-config auto-detection to force the no-variant
        # code path (where -c flags are emitted by us).
        with _mock.patch.object(mod, "_resolve_variant_config", return_value=None):
            cmd = mod._build_command(
                recipe, "linux-64", is_native=True,
                channels=("conda-forge", "bioconda"),
            )
        # Both channels passed via -c flags
        assert cmd.count("-c") == 2
        assert "conda-forge" in cmd and "bioconda" in cmd
        assert "-m" not in cmd

    def test_dry_run_does_not_invoke_subprocess(self, load_module, tmp_path):
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        with mock.patch.object(mod.subprocess, "run") as fake_run:
            result = mod.build_one_platform(recipe, "linux-64", dry_run=True)
        assert fake_run.call_count == 0
        assert result["dry_run"] is True
        assert result["success"] is True
        assert "rattler-build" in result["command"][0]

    def test_real_run_invokes_rattler_build(self, load_module, tmp_path):
        """When not in dry-run, subprocess.run is invoked with the right args."""
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        fake_proc = mock.Mock()
        fake_proc.returncode = 0
        fake_proc.stdout = "ok\n"
        fake_proc.stderr = ""
        with mock.patch.object(mod.shutil, "which", return_value="/fake/rattler-build"), \
             mock.patch.object(mod.subprocess, "run", return_value=fake_proc) as fake_run:
            result = mod.build_one_platform(recipe, "linux-aarch64")
        assert result["success"] is True
        assert result["returncode"] == 0
        # subprocess.run called with our constructed command list
        called_cmd = fake_run.call_args[0][0]
        assert "--target-platform" in called_cmd
        assert "linux-aarch64" in called_cmd
        assert "--no-test" in called_cmd

    def test_missing_rattler_build_returns_clear_error(
        self, load_module, tmp_path,
    ):
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        with mock.patch.object(mod.shutil, "which", return_value=None):
            result = mod.build_one_platform(recipe, "linux-64")
        assert result["success"] is False
        assert "rattler-build" in result["error"]

    def test_noarch_short_circuits_to_native_only(
        self, load_module, tmp_path,
    ):
        """`build_all_platforms` on a noarch recipe → only the native build."""
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(NOARCH_RECIPE_YAML)
        result = mod.build_all_platforms(recipe, dry_run=True)
        assert result["noarch_short_circuit"] is True
        assert len(result["platforms_attempted"]) == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["platform"] == mod.detect_native_platform()

    def test_compiled_runs_all_platforms(self, load_module, tmp_path):
        """Compiled recipes attempt every platform in sequence."""
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        result = mod.build_all_platforms(recipe, dry_run=True)
        assert result["noarch_short_circuit"] is False
        assert len(result["results"]) == 5
        platforms = {r["platform"] for r in result["results"]}
        assert platforms == set(mod.ALL_PLATFORMS)
        # Each per-platform command passes the correct --target-platform
        for r in result["results"]:
            assert r["platform"] in r["command"]

    def test_unknown_platform_argument_rejected(self, script_runner, tmp_path):
        """argparse choices should reject unknown platforms."""
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        rc, _, err = script_runner(
            "local_builder.py", str(recipe), "--platform", "freebsd-64",
        )
        assert rc != 0
        assert "freebsd-64" in err or "invalid choice" in err.lower()

    # ── macOS SDK setup / detection / env injection ────────────────────────

    def test_find_osx_sdk_uses_env_var_when_set(
        self, load_module, tmp_path, monkeypatch,
    ):
        mod = load_module("local_builder.py")
        # Layout: tmp_path/SDKs/MacOSX11.0.sdk/
        sdk_root = tmp_path / "SDKs"
        (sdk_root / "MacOSX11.0.sdk").mkdir(parents=True)
        monkeypatch.setenv("OSX_SDK_DIR", str(sdk_root))
        result = mod.find_osx_sdk("11.0")
        assert result == sdk_root

    def test_find_osx_sdk_finds_repo_sdks_dir(
        self, load_module, tmp_path, monkeypatch,
    ):
        mod = load_module("local_builder.py")
        # Layout: tmp_path/SDKs/MacOSX11.0.sdk/  with no env var set
        sdk_root = tmp_path / "SDKs"
        (sdk_root / "MacOSX11.0.sdk").mkdir(parents=True)
        monkeypatch.delenv("OSX_SDK_DIR", raising=False)
        result = mod.find_osx_sdk("11.0", repo_root=tmp_path)
        assert result == sdk_root

    def test_find_osx_sdk_returns_none_when_missing(
        self, load_module, tmp_path, monkeypatch,
    ):
        mod = load_module("local_builder.py")
        monkeypatch.delenv("OSX_SDK_DIR", raising=False)
        # Empty repo + non-existent home — must return None, not crash
        empty = tmp_path / "empty-repo"
        empty.mkdir()
        # Stub HOME so we don't accidentally find a real SDK in the runner's $HOME
        monkeypatch.setenv("HOME", str(tmp_path / "stub-home"))
        result = mod.find_osx_sdk("11.0", repo_root=empty)
        assert result is None

    def test_find_osx_sdk_version_specific(
        self, load_module, tmp_path, monkeypatch,
    ):
        """Only the requested version counts — other SDK versions don't
        satisfy the lookup."""
        mod = load_module("local_builder.py")
        sdks = tmp_path / "SDKs"
        (sdks / "MacOSX10.13.sdk").mkdir(parents=True)
        monkeypatch.delenv("OSX_SDK_DIR", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path / "stub-home"))
        # Looking for 11.0 — 10.13 doesn't satisfy
        assert mod.find_osx_sdk("11.0", repo_root=tmp_path) is None
        # Looking for 10.13 — found
        assert mod.find_osx_sdk("10.13", repo_root=tmp_path) == sdks

    def test_setup_osx_sdk_requires_license_acceptance(
        self, load_module, tmp_path,
    ):
        """No --accept-apple-sdk-license → setup refuses, no download."""
        mod = load_module("local_builder.py")
        result = mod.setup_osx_sdk(
            tmp_path / "SDKs", sdk_version="11.0", accept_license=False,
        )
        assert result["success"] is False
        assert result["error"] == "license-not-accepted"
        # Nothing was downloaded / extracted
        assert not (tmp_path / "SDKs" / "MacOSX11.0.sdk").exists()

    def test_setup_osx_sdk_short_circuits_when_already_present(
        self, load_module, tmp_path,
    ):
        """Re-running setup with an existing SDK directory is a no-op."""
        mod = load_module("local_builder.py")
        sdks = tmp_path / "SDKs"
        (sdks / "MacOSX11.0.sdk").mkdir(parents=True)
        result = mod.setup_osx_sdk(
            sdks, sdk_version="11.0", accept_license=True,
        )
        assert result["success"] is True
        assert result["already_present"] is True

    def test_setup_osx_sdk_downloads_with_mocked_requests(
        self, load_module, tmp_path,
    ):
        """Happy path with the network mocked — downloads + extracts."""
        import io
        import tarfile
        from unittest import mock as _mock

        mod = load_module("local_builder.py")
        # Build a tiny in-memory tar.xz containing MacOSX11.0.sdk/<file>
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:xz") as tf:
            info = tarfile.TarInfo(name="MacOSX11.0.sdk/SDKSettings.plist")
            data = b"<plist></plist>\n"
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        tarball_bytes = buf.getvalue()

        # Mock requests.get to return our synthetic tarball as a streaming response
        fake_resp = _mock.MagicMock()
        fake_resp.iter_content = lambda chunk_size: [tarball_bytes]
        fake_resp.raise_for_status = lambda: None
        fake_resp.__enter__ = _mock.Mock(return_value=fake_resp)
        fake_resp.__exit__ = _mock.Mock(return_value=False)

        with _mock.patch.object(mod, "requests") as fake_requests:
            fake_requests.get.return_value = fake_resp
            fake_requests.RequestException = Exception
            result = mod.setup_osx_sdk(
                tmp_path / "SDKs",
                sdk_version="11.0",
                accept_license=True,
                timeout=30,
            )

        assert result["success"] is True
        assert result["already_present"] is False
        assert (tmp_path / "SDKs" / "MacOSX11.0.sdk" / "SDKSettings.plist").exists()

    def test_check_reports_sdk_path_when_present(
        self, load_module, tmp_path, monkeypatch,
    ):
        """`--check` surfaces the detected SDK in osx-* platform notes."""
        mod = load_module("local_builder.py")
        sdks = tmp_path / "SDKs"
        (sdks / "MacOSX11.0.sdk").mkdir(parents=True)
        monkeypatch.setenv("OSX_SDK_DIR", str(sdks))
        report = mod.diagnose_environment("11.0")
        assert report["osx_sdk_detected"] == str(sdks)
        for plat in ("osx-64", "osx-arm64"):
            note = report["platform_support"][plat]
            assert "✓" in note or str(sdks) in note

    def test_check_warns_when_sdk_missing(
        self, load_module, tmp_path, monkeypatch,
    ):
        mod = load_module("local_builder.py")
        monkeypatch.delenv("OSX_SDK_DIR", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path / "stub-home"))
        # Move the working dir to a place with no SDKs folder so the
        # repo-root candidate doesn't accidentally find one.
        monkeypatch.chdir(tmp_path)
        report = mod.diagnose_environment("11.0")
        # When no SDK is found AND no env var, the note should hint at
        # running --setup-osx-sdk
        for plat in ("osx-64", "osx-arm64"):
            assert "NO macOS SDK found" in report["platform_support"][plat] \
                or report["osx_sdk_detected"] is not None  # detected via real $HOME

    def test_build_one_platform_injects_osx_sdk_dir(
        self, load_module, tmp_path, monkeypatch,
    ):
        """For osx-* targets, build_one_platform sets OSX_SDK_DIR in the
        subprocess env when an SDK is found."""
        mod = load_module("local_builder.py")
        # Prepare an SDK so find_osx_sdk succeeds
        sdks = tmp_path / "SDKs"
        (sdks / "MacOSX11.0.sdk").mkdir(parents=True)
        monkeypatch.setenv("OSX_SDK_DIR", str(sdks))

        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)

        from unittest import mock as _mock
        fake_proc = _mock.Mock()
        fake_proc.returncode = 0
        fake_proc.stdout = "ok\n"
        fake_proc.stderr = ""
        with _mock.patch.object(mod.shutil, "which", return_value="/fake/rb"), \
             _mock.patch.object(mod.subprocess, "run", return_value=fake_proc) as fake_run:
            mod.build_one_platform(recipe, "osx-arm64")
        # subprocess env passed in; OSX_SDK_DIR present and points at our dir
        env = fake_run.call_args.kwargs["env"]
        assert env["OSX_SDK_DIR"] == str(sdks)

    def test_build_one_platform_does_not_override_existing_sdk_env(
        self, load_module, tmp_path, monkeypatch,
    ):
        """If the user already set OSX_SDK_DIR, we respect their value."""
        mod = load_module("local_builder.py")
        custom = tmp_path / "custom-sdks"
        (custom / "MacOSX11.0.sdk").mkdir(parents=True)
        monkeypatch.setenv("OSX_SDK_DIR", str(custom))

        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)

        from unittest import mock as _mock
        fake_proc = _mock.Mock()
        fake_proc.returncode = 0
        fake_proc.stdout = ""
        fake_proc.stderr = ""
        with _mock.patch.object(mod.shutil, "which", return_value="/fake/rb"), \
             _mock.patch.object(mod.subprocess, "run", return_value=fake_proc) as fake_run:
            mod.build_one_platform(recipe, "osx-64")
        env = fake_run.call_args.kwargs["env"]
        # Our injection only happens when OSX_SDK_DIR is unset; with it set,
        # the existing value passes through unchanged.
        assert env["OSX_SDK_DIR"] == str(custom)

    def test_build_one_platform_no_sdk_injection_for_linux(
        self, load_module, tmp_path, monkeypatch,
    ):
        """Linux/win targets must NOT have OSX_SDK_DIR injected."""
        mod = load_module("local_builder.py")
        monkeypatch.delenv("OSX_SDK_DIR", raising=False)
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)

        from unittest import mock as _mock
        fake_proc = _mock.Mock()
        fake_proc.returncode = 0
        fake_proc.stdout = ""
        fake_proc.stderr = ""
        with _mock.patch.object(mod.shutil, "which", return_value="/fake/rb"), \
             _mock.patch.object(mod.subprocess, "run", return_value=fake_proc) as fake_run:
            mod.build_one_platform(recipe, "linux-aarch64")
        env = fake_run.call_args.kwargs["env"]
        assert "OSX_SDK_DIR" not in env

    def test_setup_osx_sdk_cli_flag_without_license_fails(
        self, script_runner,
    ):
        """`--setup-osx-sdk` without --accept-apple-sdk-license must refuse."""
        rc, out, _ = script_runner(
            "local_builder.py", "--setup-osx-sdk",
        )
        assert rc != 0
        result = json.loads(out)
        assert result["success"] is False
        assert "license" in result.get("error", "").lower()

    def test_dry_run_all_platforms_via_cli(self, script_runner, tmp_path):
        """End-to-end CLI smoke: --all-platforms --dry-run prints JSON
        with one entry per platform."""
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        rc, out, _ = script_runner(
            "local_builder.py", str(recipe), "--all-platforms", "--dry-run",
        )
        assert rc == 0
        result = json.loads(out)
        assert len(result["results"]) == 5
        assert result["all_success"] is True

    # ── Cross-shim wiring (install_name_tool) ──────────────────────────────

    def test_cross_shim_dir_ships_install_name_tool(self, load_module):
        """The repo ships an executable install_name_tool shim alongside
        the script — it's what we prepend to PATH for osx-* cross-builds."""
        import os as _os
        mod = load_module("local_builder.py")
        shim = mod.CROSS_SHIMS_DIR / "install_name_tool"
        assert mod.CROSS_SHIMS_DIR.is_dir(), (
            f"cross-shims dir missing: {mod.CROSS_SHIMS_DIR}"
        )
        assert shim.is_file(), f"install_name_tool shim missing: {shim}"
        assert _os.access(shim, _os.X_OK), (
            f"install_name_tool shim is not executable: {shim}"
        )

    def test_build_one_platform_prepends_cross_shim_dir_for_osx(
        self, load_module, tmp_path, monkeypatch,
    ):
        """For osx-* cross-builds, CROSS_SHIMS_DIR is prepended to PATH so
        rattler-build's post-build relink finds an install_name_tool."""
        mod = load_module("local_builder.py")
        sdks = tmp_path / "SDKs"
        (sdks / "MacOSX11.0.sdk").mkdir(parents=True)
        monkeypatch.setenv("OSX_SDK_DIR", str(sdks))

        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)

        from unittest import mock as _mock
        fake_proc = _mock.Mock()
        fake_proc.returncode = 0
        fake_proc.stdout = ""
        fake_proc.stderr = ""
        with _mock.patch.object(mod.shutil, "which", return_value="/fake/rb"), \
             _mock.patch.object(mod.subprocess, "run", return_value=fake_proc) as fake_run:
            mod.build_one_platform(recipe, "osx-arm64")
        env = fake_run.call_args.kwargs["env"]
        # First entry of PATH must be the shim dir
        first_path_entry = env["PATH"].split(os.pathsep, 1)[0]
        assert first_path_entry == str(mod.CROSS_SHIMS_DIR)

    def test_build_one_platform_does_not_inject_shim_for_non_osx(
        self, load_module, tmp_path, monkeypatch,
    ):
        """linux/win cross-builds don't need the install_name_tool shim,
        so CROSS_SHIMS_DIR must NOT appear at the head of PATH for them."""
        mod = load_module("local_builder.py")
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)

        from unittest import mock as _mock
        fake_proc = _mock.Mock()
        fake_proc.returncode = 0
        fake_proc.stdout = ""
        fake_proc.stderr = ""
        with _mock.patch.object(mod.shutil, "which", return_value="/fake/rb"), \
             _mock.patch.object(mod.subprocess, "run", return_value=fake_proc) as fake_run:
            mod.build_one_platform(recipe, "linux-aarch64")
        env = fake_run.call_args.kwargs["env"]
        first_path_entry = env.get("PATH", "").split(os.pathsep, 1)[0]
        assert first_path_entry != str(mod.CROSS_SHIMS_DIR)

    def test_build_one_platform_sets_local_builder_output_dir_for_osx(
        self, load_module, tmp_path, monkeypatch,
    ):
        """LOCAL_BUILDER_OUTPUT_DIR is the hint the install_name_tool shim
        uses to glob ``<output>/bld/*/build_env/bin``. Must be set
        whenever output_dir is provided for an osx-* cross-build."""
        mod = load_module("local_builder.py")
        sdks = tmp_path / "SDKs"
        (sdks / "MacOSX11.0.sdk").mkdir(parents=True)
        monkeypatch.setenv("OSX_SDK_DIR", str(sdks))

        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(COMPILED_RECIPE_YAML)
        out = tmp_path / "myout"
        out.mkdir()

        from unittest import mock as _mock
        fake_proc = _mock.Mock()
        fake_proc.returncode = 0
        fake_proc.stdout = ""
        fake_proc.stderr = ""
        with _mock.patch.object(mod.shutil, "which", return_value="/fake/rb"), \
             _mock.patch.object(mod.subprocess, "run", return_value=fake_proc) as fake_run:
            mod.build_one_platform(recipe, "osx-arm64", output_dir=out)
        env = fake_run.call_args.kwargs["env"]
        # Resolved (absolute) form, matching how local_builder.py computes it
        assert env["LOCAL_BUILDER_OUTPUT_DIR"] == str(out.resolve())
