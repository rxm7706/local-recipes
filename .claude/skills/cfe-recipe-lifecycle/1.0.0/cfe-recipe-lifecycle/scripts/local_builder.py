#!/usr/bin/env python3
"""
Docker-less local builder for conda-forge recipes.

Wraps ``rattler-build build`` with per-target-platform flags so a single
Linux machine can validate builds across linux-64, linux-aarch64, osx-64,
osx-arm64, and win-64. Cross-platform builds skip the test phase since
the produced binaries can't run on the host; native linux-64 runs full
build + test.

Pattern source — the user's working invocations:
    rattler-build build -r <recipe> -c conda-forge
    rattler-build build -r <recipe> -c conda-forge --target-platform linux-aarch64 --no-test
    rattler-build build -r <recipe> -c conda-forge --target-platform osx-64    --no-test
    rattler-build build -r <recipe> -c conda-forge --target-platform osx-arm64 --no-test
    rattler-build build -r <recipe> -c conda-forge --target-platform win-64    --no-test --allow-symlinks-on-windows

Usage:
    python local_builder.py recipes/<name>                     # native linux-64
    python local_builder.py recipes/<name> --platform osx-arm64
    python local_builder.py recipes/<name> --all-platforms
    python local_builder.py --check                            # env diagnostic
    python local_builder.py recipes/<name> --dry-run --all-platforms
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None  # type: ignore[assignment]
    YAML_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False


# ── Platform metadata ────────────────────────────────────────────────────────

#: All target platforms we know how to drive locally.
ALL_PLATFORMS = ("linux-64", "linux-aarch64", "osx-64", "osx-arm64", "win-64")

#: Maps target-platform → the project-level variant config filename (under
#: ``.ci_support/``). The mapping is inconsistent in this project — most
#: drop the dash, but linux-aarch64 uses an underscore. We look up directly
#: rather than guessing.
PLATFORM_TO_VARIANT_FILE = {
    "linux-64": "linux64.yaml",
    "linux-aarch64": "linux_aarch64.yaml",
    "osx-64": "osx64.yaml",
    "osx-arm64": "osxarm64.yaml",
    "win-64": "win64.yaml",
}

#: The build host's native conda-forge platform, derived from `platform.machine()`.
_HOST_TO_NATIVE = {
    ("Linux", "x86_64"): "linux-64",
    ("Linux", "aarch64"): "linux-aarch64",
    ("Linux", "arm64"): "linux-aarch64",
    ("Darwin", "x86_64"): "osx-64",
    ("Darwin", "arm64"): "osx-arm64",
    ("Windows", "AMD64"): "win-64",
}


def detect_native_platform() -> str:
    """Return the host's native conda-forge target-platform string."""
    key = (platform.system(), platform.machine())
    return _HOST_TO_NATIVE.get(key, "linux-64")


# ── Recipe inspection ────────────────────────────────────────────────────────

def _normalize_recipe_path(path: Path) -> Path:
    """Accept either a recipe file or a recipe directory; return the file."""
    if path.is_file():
        return path
    if path.is_dir():
        for name in ("recipe.yaml", "meta.yaml"):
            candidate = path / name
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"No recipe.yaml or meta.yaml found at {path}")


def _is_noarch(recipe_path: Path) -> bool:
    """Return True when the recipe declares ``build.noarch:`` (any value)."""
    if not YAML_AVAILABLE:
        # If we can't parse, assume non-noarch and let the user explicitly opt in.
        return False
    assert yaml is not None
    try:
        # Strip Jinja / rattler-build templates so PyYAML can load the file.
        raw = recipe_path.read_text(encoding="utf-8")
        import re
        raw = re.sub(r"\$\{\{[^}]*\}\}", "TEMPLATE", raw)
        raw = re.sub(r"\{%[^%]*%\}", "", raw)
        raw = re.sub(r"\{\{[^}]*\}\}", "TEMPLATE", raw)
        data = yaml.safe_load(raw)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    build = data.get("build") or {}
    return bool(build.get("noarch"))


# ── macOS SDK setup ──────────────────────────────────────────────────────────

#: Default macOS SDK version. Matches the project's
#: ``.ci_support/osx64.yaml`` ``MACOSX_DEPLOYMENT_TARGET: 11.0`` floor.
DEFAULT_OSX_SDK_VERSION = "11.0"

#: Cross-build shim directory (sibling of this script). The shims
#: re-dispatch unprefixed tool calls (e.g. ``install_name_tool``) to the
#: target-triple-prefixed binaries shipped by conda-forge's
#: ``cctools_osx-*`` packages — rattler-build's post-build relink step
#: looks up the unprefixed name on Linux hosts and fails otherwise.
CROSS_SHIMS_DIR = Path(__file__).resolve().parent / "cross-shims"

#: Community mirror (the de-facto source for cross-compile setups). The
#: project's ``.gitignore`` already excludes ``MacOSX*.sdk.tar.xz`` and
#: ``SDKs/``. NOT an official Apple distribution — use of the SDK is
#: subject to Apple's licence terms.
PHRACKER_SDK_URL = (
    "https://github.com/phracker/MacOSX-SDKs/releases/download/11.3/"
    "MacOSX{version}.sdk.tar.xz"
)


def _repo_root_candidate() -> Path:
    """Best guess at the repo root.

    Walks up from this file until it finds a ``pixi.toml`` (the project's
    natural marker). Falls back to the script's grandparent if nothing's
    found — that's still inside the skill, which is fine for tests.
    """
    cur = Path(__file__).resolve().parent
    for _ in range(8):
        if (cur / "pixi.toml").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return Path(__file__).resolve().parents[3]


def find_osx_sdk(
    sdk_version: str = DEFAULT_OSX_SDK_VERSION,
    *,
    repo_root: Path | None = None,
) -> Path | None:
    """Locate a usable macOS SDK directory on this host.

    Search order (first hit wins):
      1. ``$OSX_SDK_DIR`` env var (if it points at a directory containing
         ``MacOSX<version>.sdk``)
      2. ``<repo-root>/SDKs/MacOSX<version>.sdk`` (conda-forge convention,
         matches ``.scripts/run_docker_build.sh`` / ``build-locally.py``)
      3. ``$HOME/SDKs/MacOSX<version>.sdk``

    Returns the **parent directory** that should be exported as
    ``OSX_SDK_DIR`` (i.e. the one that *contains* the ``MacOSX<v>.sdk``
    folder), not the SDK folder itself. ``None`` if nothing's found.
    """
    env_dir = os.environ.get("OSX_SDK_DIR")
    if env_dir:
        candidate = Path(env_dir)
        if (candidate / f"MacOSX{sdk_version}.sdk").is_dir():
            return candidate

    root = repo_root or _repo_root_candidate()
    for parent in (root / "SDKs", Path.home() / "SDKs"):
        if (parent / f"MacOSX{sdk_version}.sdk").is_dir():
            return parent
    return None


# Apple's macOS SDK is governed by the Xcode and Apple SDKs Agreement.
# We do not redistribute. The user is responsible for compliance.
APPLE_SDK_LICENSE_URL = "https://www.apple.com/legal/sla/docs/xcode.pdf"
APPLE_SDK_LICENSE_NOTICE = (
    "The macOS SDK is governed by the Xcode and Apple SDKs Agreement. "
    "By passing --accept-apple-sdk-license you confirm you have read and "
    f"accept the licence at {APPLE_SDK_LICENSE_URL}."
)


def setup_osx_sdk(
    target_dir: Path,
    *,
    sdk_version: str = DEFAULT_OSX_SDK_VERSION,
    accept_license: bool = False,
    download_url: str | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    """Download and extract MacOSX{version}.sdk into ``target_dir``.

    The user MUST pass ``accept_license=True`` (CLI: ``--accept-apple-sdk-license``)
    confirming they accept Apple's terms. We do not redistribute the SDK
    ourselves — it's fetched from the community mirror at
    ``github.com/phracker/MacOSX-SDKs``.
    """
    if not accept_license:
        return {
            "success": False,
            "error": "license-not-accepted",
            "message": APPLE_SDK_LICENSE_NOTICE,
        }
    if not REQUESTS_AVAILABLE:
        return {
            "success": False,
            "error": "requests library required to download the SDK",
        }
    assert requests is not None

    target_dir = target_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    sdk_subdir = target_dir / f"MacOSX{sdk_version}.sdk"
    if sdk_subdir.is_dir():
        return {
            "success": True,
            "already_present": True,
            "sdk_dir": str(target_dir),
            "sdk_subdir": str(sdk_subdir),
        }

    url = download_url or PHRACKER_SDK_URL.format(version=sdk_version)
    tarball = target_dir / f"MacOSX{sdk_version}.sdk.tar.xz"
    print(f"Downloading {url} → {tarball}", file=sys.stderr)
    try:
        with requests.get(url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            with open(tarball, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        fh.write(chunk)
    except requests.RequestException as exc:
        return {"success": False, "error": f"download failed: {exc}"}

    print(f"Extracting {tarball.name} into {target_dir}", file=sys.stderr)
    import tarfile
    try:
        # tarfile in 3.12+ requires explicit filter; "data" is the safe default
        with tarfile.open(tarball, mode="r:xz") as tf:
            tf.extractall(path=target_dir, filter="data")  # type: ignore[arg-type]
    except (tarfile.TarError, OSError) as exc:
        return {"success": False, "error": f"extraction failed: {exc}"}

    return {
        "success": True,
        "already_present": False,
        "sdk_dir": str(target_dir),
        "sdk_subdir": str(sdk_subdir),
        "downloaded_from": url,
    }


# ── Build invocation ─────────────────────────────────────────────────────────

def _variant_has_channel_sources(variant_path: Path) -> bool:
    """Return True if the variant YAML declares ``channel_sources:``.

    Cheap textual scan — we don't need to fully parse the YAML for this.
    """
    try:
        text = variant_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "channel_sources" in text


def _resolve_variant_config(
    target_platform: str, repo_root: Path | None = None,
) -> Path | None:
    """Return the path to ``.ci_support/<platform>.yaml`` if it exists.

    Conda-forge recipes that use the ``stdlib('c')`` macro require a
    variant config providing ``c_stdlib`` / ``c_stdlib_version``. The
    project ships these per-platform under ``.ci_support/``.
    """
    fname = PLATFORM_TO_VARIANT_FILE.get(target_platform)
    if not fname:
        return None
    root = repo_root or _repo_root_candidate()
    candidate = root / ".ci_support" / fname
    return candidate if candidate.is_file() else None


def _build_command(
    recipe_path: Path,
    target_platform: str,
    *,
    is_native: bool,
    channels: tuple[str, ...] = ("conda-forge",),
    output_dir: Path | None = None,
    variant_config: Path | None = None,
) -> list[str]:
    """Construct the rattler-build invocation for this platform.

    ``--no-test`` is added for cross-platform targets (the produced
    binaries can't run on the host).
    ``--allow-symlinks-on-windows`` is added for win-64 cross-builds —
    rattler-build needs it to materialise packages that use symlinks
    when targeting a filesystem that doesn't natively support them.
    ``-m <variant.yaml>`` is added when a per-platform variant config is
    available — required for any recipe that uses the ``stdlib('c')`` /
    ``compiler('c')`` macros.
    """
    cmd = [
        "rattler-build", "build",
        "-r", str(recipe_path),
    ]

    if variant_config is None:
        variant_config = _resolve_variant_config(target_platform)

    # When the variant config provides ``channel_sources:`` (the project's
    # ``.ci_support/*.yaml`` files all do), passing ``-c`` again would
    # duplicate channel input and rattler-build refuses with
    # ``channel_sources and channels cannot both be set``. Skip the
    # ``-c`` flags in that case.
    skip_channel_cli = (
        variant_config is not None and _variant_has_channel_sources(variant_config)
    )
    if not skip_channel_cli:
        for ch in channels:
            cmd += ["-c", ch]

    cmd += ["--target-platform", target_platform]
    if variant_config is not None:
        cmd += ["-m", str(variant_config)]

    if not is_native:
        cmd.append("--no-test")
        # rattler-build's default --env-isolation=strict scrubs the env,
        # which strips SDKROOT and the CONDA_OVERRIDE_* vars that cross-
        # builds rely on. ``conda-build`` mode forwards a small allow-list
        # but DOES NOT include SDKROOT, so the conda-forge clang_osx-*
        # activation script bails with "Need to set SDKROOT when cross-
        # compiling". We use ``none`` here — full host env passthrough —
        # because the only sane way to drive these activation scripts on
        # Linux is to let them see the SDKROOT we set.
        cmd += ["--env-isolation", "none"]
    if target_platform == "win-64":
        cmd.append("--allow-symlinks-on-windows")
    if output_dir is not None:
        cmd += ["--output-dir", str(output_dir)]
    return cmd


def build_one_platform(
    recipe_path: Path,
    target_platform: str,
    *,
    channels: tuple[str, ...] = ("conda-forge",),
    output_dir: Path | None = None,
    dry_run: bool = False,
    timeout: int = 3600,
) -> dict[str, Any]:
    """Run a single rattler-build for ``target_platform``.

    Returns ``{"platform": ..., "success": bool, "duration_s": float,
    "command": [...], "stdout_tail": str, "stderr_tail": str}``.
    """
    native = detect_native_platform()
    is_native = (target_platform == native)
    cmd = _build_command(
        recipe_path, target_platform,
        is_native=is_native, channels=channels, output_dir=output_dir,
    )

    if dry_run:
        return {
            "platform": target_platform,
            "is_native": is_native,
            "dry_run": True,
            "command": cmd,
            "success": True,
        }

    if shutil.which("rattler-build") is None:
        return {
            "platform": target_platform,
            "success": False,
            "error": "rattler-build not on PATH; activate the local-recipes pixi env.",
            "command": cmd,
        }

    # Inject the env vars rattler-build's solver needs for cross-builds:
    #
    #  * OSX_SDK_DIR — points clang_osx-*/clangxx_osx-* at the SDK headers
    #  * CONDA_OVERRIDE_OSX — supplies the ``__osx`` virtual-package version
    #    so recipes with ``c_stdlib_version: 11.0`` solve correctly on Linux
    #  * CONDA_OVERRIDE_GLIBC — same idea for linux-aarch64 cross-builds
    #
    # Existing user-set values take precedence (we never overwrite).
    env = os.environ.copy()
    if target_platform in ("osx-64", "osx-arm64"):
        sdk_dir = (
            Path(env["OSX_SDK_DIR"]) if env.get("OSX_SDK_DIR") else find_osx_sdk()
        )
        if sdk_dir is not None:
            env["OSX_SDK_DIR"] = str(sdk_dir)
            # SDKROOT must point at the specific MacOSX<ver>.sdk subdir;
            # conda-forge's clang_osx-*/clangxx_osx-* activation scripts
            # bail with "Need to set SDKROOT when cross-compiling"
            # otherwise.
            sdk_subdir = sdk_dir / f"MacOSX{DEFAULT_OSX_SDK_VERSION}.sdk"
            if sdk_subdir.is_dir():
                env.setdefault("SDKROOT", str(sdk_subdir))
        env.setdefault("CONDA_OVERRIDE_OSX", DEFAULT_OSX_SDK_VERSION)
        env.setdefault("MACOSX_DEPLOYMENT_TARGET", DEFAULT_OSX_SDK_VERSION)
        # Prepend the cross-shim dir so rattler-build's post-build
        # relink step finds an ``install_name_tool`` to call. The shim
        # re-dispatches to ``<triple>-install_name_tool`` from
        # cctools_osx-* in the build env. We also set
        # ``LOCAL_BUILDER_OUTPUT_DIR`` so the shim can glob
        # ``<output>/bld/*/build_env/bin`` — rattler-build's relink
        # subprocess inherits no build-context env vars, so this is the
        # only way the shim can locate the cross-toolchain.
        if CROSS_SHIMS_DIR.is_dir():
            env["PATH"] = f"{CROSS_SHIMS_DIR}{os.pathsep}{env.get('PATH', '')}"
        if output_dir is not None:
            env["LOCAL_BUILDER_OUTPUT_DIR"] = str(output_dir.resolve())
    elif target_platform == "linux-aarch64":
        env.setdefault("CONDA_OVERRIDE_GLIBC", "2.17")

    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "platform": target_platform,
            "success": False,
            "error": f"rattler-build timed out after {timeout}s",
            "command": cmd,
        }
    duration = time.monotonic() - started

    return {
        "platform": target_platform,
        "is_native": is_native,
        "success": proc.returncode == 0,
        "returncode": proc.returncode,
        "duration_s": round(duration, 1),
        "command": cmd,
        # Tails only — full logs are noisy
        "stdout_tail": "\n".join((proc.stdout or "").splitlines()[-20:]),
        "stderr_tail": "\n".join((proc.stderr or "").splitlines()[-20:]),
    }


def build_all_platforms(
    recipe_path: Path,
    *,
    platforms: tuple[str, ...] = ALL_PLATFORMS,
    channels: tuple[str, ...] = ("conda-forge",),
    output_dir: Path | None = None,
    dry_run: bool = False,
    timeout: int = 3600,
) -> dict[str, Any]:
    """Run rattler-build across multiple target platforms in sequence.

    For ``noarch`` recipes, only the native platform is attempted — the
    produced package works everywhere by design.
    """
    if _is_noarch(recipe_path):
        native = detect_native_platform()
        result = build_one_platform(
            recipe_path, native,
            channels=channels, output_dir=output_dir,
            dry_run=dry_run, timeout=timeout,
        )
        return {
            "recipe": str(recipe_path),
            "noarch_short_circuit": True,
            "platforms_attempted": [native],
            "results": [result],
            "all_success": result["success"],
        }

    results = []
    for plat in platforms:
        results.append(build_one_platform(
            recipe_path, plat,
            channels=channels, output_dir=output_dir,
            dry_run=dry_run, timeout=timeout,
        ))
    return {
        "recipe": str(recipe_path),
        "noarch_short_circuit": False,
        "platforms_attempted": list(platforms),
        "results": results,
        "all_success": all(r.get("success") for r in results),
    }


# ── Diagnostic mode (--check) ────────────────────────────────────────────────

def diagnose_environment(
    sdk_version: str = DEFAULT_OSX_SDK_VERSION,
) -> dict[str, Any]:
    """Report what's available for local cross-platform builds."""
    detected_sdk = find_osx_sdk(sdk_version)
    findings: dict[str, Any] = {
        "host_system": platform.system(),
        "host_machine": platform.machine(),
        "native_platform": detect_native_platform(),
        "rattler_build_path": shutil.which("rattler-build"),
        "rattler_build_version": None,
        "osx_sdk_dir_env": os.environ.get("OSX_SDK_DIR"),
        "osx_sdk_detected": str(detected_sdk) if detected_sdk else None,
        "osx_sdk_version_target": sdk_version,
        "yaml_available": YAML_AVAILABLE,
        "platform_support": {},
    }
    if findings["rattler_build_path"]:
        try:
            proc = subprocess.run(
                ["rattler-build", "--version"], capture_output=True,
                text=True, timeout=10, check=False,
            )
            findings["rattler_build_version"] = (proc.stdout or "").strip()
        except Exception:
            pass

    native = findings["native_platform"]
    for plat in ALL_PLATFORMS:
        if plat == native:
            note = "native — full build + test"
        elif plat == "win-64":
            note = (
                "cross-build with --no-test --allow-symlinks-on-windows; "
                "MSVC-required packages may fail (use GitHub Actions for "
                "those)"
            )
        elif plat in ("osx-64", "osx-arm64"):
            if detected_sdk:
                note = f"cross-build with --no-test (SDK at {detected_sdk} ✓)"
            else:
                note = (
                    "cross-build with --no-test (NO macOS SDK found — run "
                    "`pixi run build-local-setup-sdk --accept-apple-sdk-license` "
                    "to download MacOSX SDK to <repo>/SDKs/)"
                )
        else:
            note = "cross-build with --no-test"
        findings["platform_support"][plat] = note
    return findings


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Docker-less local builder — wraps rattler-build with "
                    "per-platform flags for cross-platform validation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  local_builder.py recipes/foo                  # native build+test\n"
            "  local_builder.py recipes/foo -p osx-arm64     # one cross-build\n"
            "  local_builder.py recipes/foo --all-platforms  # all 5 in sequence\n"
            "  local_builder.py --check                      # env diagnostic\n"
        ),
    )
    parser.add_argument(
        "recipe_path", type=Path, nargs="?",
        help="Recipe file or directory (omit when using --check).",
    )
    parser.add_argument(
        "--platform", "-p", choices=ALL_PLATFORMS, default=None,
        help="Target platform (default: host's native platform).",
    )
    parser.add_argument(
        "--all-platforms", action="store_true", dest="all_platforms",
        help="Build for every supported platform in sequence.",
    )
    parser.add_argument(
        "--channel", "-c", action="append", default=None,
        help="Conda channel (default: conda-forge). Pass multiple times to add.",
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path, default=None,
        help="rattler-build output directory (default: ./output).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the rattler-build command(s) but don't run them.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Diagnose what's available for local cross-platform builds.",
    )
    parser.add_argument(
        "--setup-osx-sdk", action="store_true", dest="setup_osx_sdk",
        help="Download and extract the macOS SDK to <repo-root>/SDKs/. "
             "Requires --accept-apple-sdk-license. Apple's licence terms "
             "apply to use of the SDK; see "
             f"{APPLE_SDK_LICENSE_URL}",
    )
    parser.add_argument(
        "--accept-apple-sdk-license", action="store_true",
        dest="accept_apple_sdk_license",
        help="Confirm acceptance of Apple's macOS SDK licence terms. "
             "Required for --setup-osx-sdk.",
    )
    parser.add_argument(
        "--sdk-version", default=DEFAULT_OSX_SDK_VERSION,
        help=f"macOS SDK version to look for / download (default: "
             f"{DEFAULT_OSX_SDK_VERSION}).",
    )
    parser.add_argument(
        "--sdk-dir", type=Path, default=None,
        help="Override the directory where the SDK is located / installed "
             "(default: <repo-root>/SDKs/).",
    )
    parser.add_argument(
        "--timeout", type=int, default=3600,
        help="Per-platform build timeout in seconds (default: 3600).",
    )
    args = parser.parse_args()

    if args.check:
        print(json.dumps(diagnose_environment(args.sdk_version), indent=2))
        sys.exit(0)

    if args.setup_osx_sdk:
        target_dir = (args.sdk_dir or (_repo_root_candidate() / "SDKs")).expanduser()
        result = setup_osx_sdk(
            target_dir,
            sdk_version=args.sdk_version,
            accept_license=args.accept_apple_sdk_license,
        )
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("success") else 1)

    if args.recipe_path is None:
        parser.error("recipe_path is required unless --check is passed")

    try:
        recipe_path = _normalize_recipe_path(args.recipe_path)
    except FileNotFoundError as exc:
        print(json.dumps({"success": False, "error": str(exc)}, indent=2))
        sys.exit(1)

    channels = tuple(args.channel) if args.channel else ("conda-forge",)

    if args.all_platforms:
        result = build_all_platforms(
            recipe_path,
            channels=channels, output_dir=args.output_dir,
            dry_run=args.dry_run, timeout=args.timeout,
        )
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["all_success"] else 1)

    target = args.platform or detect_native_platform()
    result = build_one_platform(
        recipe_path, target,
        channels=channels, output_dir=args.output_dir,
        dry_run=args.dry_run, timeout=args.timeout,
    )
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
