#!/usr/bin/env python3
"""
Intelligent Build Failure Analyzer for conda-forge recipes.

Analyzes a build error log against a library of known patterns and returns
structured, actionable diagnoses. Returns ALL matches found, not just the first,
so multi-root-cause failures can be fully diagnosed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Pattern data model
# ---------------------------------------------------------------------------

class ErrorPattern:
    """A known error pattern and its corresponding solution."""
    __slots__ = ("name", "category", "regex", "diagnosis", "suggestion")

    def __init__(
        self,
        name: str,
        category: str,
        regex: re.Pattern[str],
        diagnosis: str,
        suggestion: dict[str, Any],
    ) -> None:
        self.name = name
        self.category = category
        self.regex = regex
        self.diagnosis = diagnosis
        self.suggestion = suggestion


# ---------------------------------------------------------------------------
# Error library — 30 patterns across 9 categories
# ---------------------------------------------------------------------------
# Suggestion actions understood by recipe_editor.py:
#   add_to_list   — append value to a YAML list at path
#   update        — set a scalar value at path
#   add_to_cbc    — add key/value to conda_build_config.yaml
#   set_env       — set an environment variable in build.sh
#   informational — no automated fix; diagnosis only

ERROR_LIBRARY: list[ErrorPattern] = [

    # -----------------------------------------------------------------------
    # CATEGORY: COMPILER
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="COMPILER_NOT_FOUND",
        category="COMPILER",
        regex=re.compile(
            r"(gfortran|gcc|g\+\+|clang|clang\+\+|cl\.exe|flang|ifort)"
            r"(?:\.exe)?\s*:\s*(command not found|not recognized as an internal or external command)",
            re.IGNORECASE,
        ),
        diagnosis="A required compiler was not found in the build environment.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "${{ compiler('c') }}",
            "comment": "Add ${{ compiler('c') }} and/or ${{ compiler('cxx') }} / ${{ compiler('fortran') }} as needed.",
        },
    ),
    ErrorPattern(
        name="MISSING_STDLIB",
        category="COMPILER",
        regex=re.compile(
            r"(compiler jinja function requires stdlib"
            r"|missing stdlib\('c'\)"
            r"|You need to add `stdlib` to your build requirements)",
            re.IGNORECASE,
        ),
        diagnosis=(
            "A compiler was declared without the required ${{ stdlib('c') }} entry. "
            "conda-forge CI enforces this for all compiled packages."
        ),
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "${{ stdlib('c') }}",
            "comment": "Every recipe that uses compiler() must also declare stdlib('c') immediately after.",
        },
    ),
    ErrorPattern(
        name="CMAKE_COMPILER_NOT_SET",
        category="COMPILER",
        regex=re.compile(
            r"No CMAKE_(?:C|CXX|Fortran)_COMPILER could be found"
            r"|CMAKE_(?:C|CXX)_COMPILER(?:-NOTFOUND| not set)",
            re.IGNORECASE,
        ),
        diagnosis="CMake could not locate a C/C++ compiler. The conda compiler activation script may not have been sourced.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "${{ compiler('c') }}",
            "comment": "Add compiler() to build requirements and ensure the build script sources $CONDA_BUILD_SYSROOT or uses cmake via conda.",
        },
    ),
    ErrorPattern(
        name="INCORRECT_CPP_STANDARD",
        category="COMPILER",
        regex=re.compile(r"error: C\+\+(\d{2}) is required but the CXX standard is (\d{2})"),
        diagnosis="The source requires a newer C++ standard than the conda-forge default.",
        suggestion={
            "action": "add_to_cbc",
            "key": "cxx_std",
            "value": "17",
            "comment": "Add cxx_std: [17] (or 20) to conda_build_config.yaml.",
        },
    ),
    ErrorPattern(
        name="FORTRAN_MODULE_VERSION_MISMATCH",
        category="COMPILER",
        regex=re.compile(
            r"Cannot read module file '([^']+\.mod)' .*different version of GNU Fortran",
            re.IGNORECASE,
        ),
        diagnosis="A Fortran .mod file was compiled with a different gfortran version than the current build.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "${{ compiler('fortran') }}",
            "comment": "Ensure all Fortran dependencies and the recipe use the same compiler version from conda-forge.",
        },
    ),

    # -----------------------------------------------------------------------
    # CATEGORY: BUILD_TOOLS
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="CMAKE_NOT_FOUND",
        category="BUILD_TOOLS",
        regex=re.compile(r"cmake(?:\.exe)?\s*:\s*(?:command not found|not found in PATH)", re.IGNORECASE),
        diagnosis="cmake was not found in the build environment.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "cmake",
            "comment": "Add cmake to the build requirements.",
        },
    ),
    ErrorPattern(
        name="NINJA_NOT_FOUND",
        category="BUILD_TOOLS",
        regex=re.compile(
            r"CMake was unable to find a build program corresponding to \"Ninja\""
            r"|ninja(?:\.exe)?\s*:\s*command not found",
            re.IGNORECASE,
        ),
        diagnosis="Ninja build system was not found. CMake defaults to Ninja on conda-forge.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "ninja",
            "comment": "Add ninja to the build requirements.",
        },
    ),
    ErrorPattern(
        name="PKG_CONFIG_NOT_FOUND",
        category="BUILD_TOOLS",
        regex=re.compile(
            r"pkg-config\s*:\s*command not found"
            r"|Package '([^']+)', required by '([^']+)', not found"
            r"|No package '([^']+)' found",
            re.IGNORECASE,
        ),
        diagnosis="pkg-config or a required .pc file was missing from the build environment.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "pkg-config",
            "comment": "Add pkg-config to build requirements. Also ensure the library providing the .pc file is in host requirements.",
        },
    ),
    ErrorPattern(
        name="CMAKE_FIND_PACKAGE_ERROR",
        category="BUILD_TOOLS",
        regex=re.compile(
            r"CMake Error.*\n?.*(?:find_package|find_dependency)\(\).*\n?.*"
            r"Could not find a package configuration file provided by \"([\w]+)\"",
            re.IGNORECASE,
        ),
        diagnosis="CMake could not locate a required dependency's config file. The package is likely missing from host requirements.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.host",
            "value": "PLACEHOLDER",
            "comment": "Add the missing CMake package to host requirements.",
        },
    ),

    # -----------------------------------------------------------------------
    # CATEGORY: LINKER
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="MISSING_HEADER_FILE",
        category="LINKER",
        regex=re.compile(r"fatal error: '([^']+?)' file not found", re.IGNORECASE),
        diagnosis="A C/C++ header file was not found, indicating a missing host dependency.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.host",
            "value": "PLACEHOLDER",
            "comment": "Find which conda-forge package provides the missing header and add it to host requirements.",
        },
    ),
    ErrorPattern(
        name="UNDEFINED_LINKER_REFERENCE",
        category="LINKER",
        regex=re.compile(
            r"(?:undefined reference to|unresolved external symbol)[:\s]+[`'\"]?([\w:~<>]+)",
            re.IGNORECASE,
        ),
        diagnosis="The linker could not find the implementation for a symbol, indicating a missing library.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.host",
            "value": "PLACEHOLDER",
            "comment": "Find which conda-forge package provides the missing symbol and add it to host requirements.",
        },
    ),
    ErrorPattern(
        name="LINKER_CANNOT_FIND_LIBRARY",
        category="LINKER",
        regex=re.compile(r"cannot find -l(\w+)", re.IGNORECASE),
        diagnosis="The linker could not find a required library (-lfoo). The library or its dev package is missing.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.host",
            "value": "PLACEHOLDER",
            "comment": "Add the conda-forge package that provides libFOO to host requirements.",
        },
    ),
    ErrorPattern(
        name="MISSING_SHARED_LIBRARY_AT_RUNTIME",
        category="LINKER",
        regex=re.compile(
            r"error while loading shared libraries: (lib[\w.+-]+\.so[\d.]*):"
            r" cannot open shared object file",
            re.IGNORECASE,
        ),
        diagnosis="A shared library was missing at runtime. The package providing it must be added to run requirements.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.run",
            "value": "PLACEHOLDER",
            "comment": "Find which conda-forge package provides the missing .so and add it to run requirements.",
        },
    ),
    ErrorPattern(
        name="MACOS_DYLIB_NOT_LOADED",
        category="LINKER",
        regex=re.compile(
            r"Library not loaded: @rpath/([\w./+-]+\.dylib)",
            re.IGNORECASE,
        ),
        diagnosis="A macOS dynamic library could not be loaded via @rpath. The RPATH may be missing or the library is absent.",
        suggestion={
            "action": "informational",
            "comment": (
                "Add the library to run requirements. "
                "If RPATH is wrong, use install_name_tool or set CMAKE_INSTALL_RPATH=$PREFIX/lib in the build script."
            ),
        },
    ),

    # -----------------------------------------------------------------------
    # CATEGORY: PYTHON
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="MODULE_NOT_FOUND_AT_TEST",
        category="PYTHON",
        regex=re.compile(
            r"(?:ModuleNotFoundError|ImportError): No module named '([\w.]+)'",
            re.IGNORECASE,
        ),
        diagnosis=(
            "A Python module could not be imported during the test phase. "
            "Either the package was not installed correctly or a test dependency is missing."
        ),
        suggestion={
            "action": "add_to_list",
            "path": "tests[0].requirements.run",
            "value": "PLACEHOLDER",
            "comment": "Add the missing module's package to test run requirements, or verify the package installs all __init__.py files.",
        },
    ),
    ErrorPattern(
        name="PYTHON_ABI_UNDEFINED_SYMBOL",
        category="PYTHON",
        regex=re.compile(
            r"ImportError: (?:/[^\s]+/)?[\w.+-]+\.so(?:\.\d+)*:"
            r" undefined symbol: (PyInit_\w+|Py_\w+)",
            re.IGNORECASE,
        ),
        diagnosis=(
            "A Python C extension has an undefined PyInit_ symbol, typically caused by a Python "
            "version mismatch between build time and test/runtime."
        ),
        suggestion={
            "action": "informational",
            "comment": (
                "Ensure python appears in both host and run requirements with matching version constraints. "
                "The extension must be rebuilt against the runtime Python version."
            ),
        },
    ),
    ErrorPattern(
        name="GLIBCXX_VERSION_NOT_FOUND",
        category="PYTHON",
        regex=re.compile(
            r"(?:ImportError|OSError):.*libstdc\+\+\.so\.6:"
            r" version `(GLIBCXX_[\d.]+)' not found",
            re.IGNORECASE,
        ),
        diagnosis=(
            "A compiled extension requires a newer GLIBCXX symbol than is available "
            "in the runtime libstdc++. The package was likely built against a newer compiler."
        ),
        suggestion={
            "action": "add_to_list",
            "path": "requirements.run",
            "value": "libstdcxx-ng",
            "comment": "Add libstdcxx-ng to run requirements to ensure the correct runtime C++ standard library is present.",
        },
    ),
    ErrorPattern(
        name="PIP_CHECK_FAILED",
        category="PYTHON",
        regex=re.compile(
            r"(?:has requirement|requires) ([\w-]+(?: [\w<>=!,]+)?) but you have ([\w-]+ [\d.]+)",
            re.IGNORECASE,
        ),
        diagnosis="pip check found incompatible installed packages. A run dependency has an unsatisfied version constraint.",
        suggestion={
            "action": "informational",
            "comment": (
                "Review run requirements for the conflicting package. "
                "Pin the dependency version or relax the constraint to resolve the conflict."
            ),
        },
    ),
    ErrorPattern(
        name="PYTHON_REQUIRES_NEWER",
        category="PYTHON",
        regex=re.compile(
            r"(?:Requires-Python|python_requires).*?>=\s*([\d.]+).*?"
            r"(?:but you have|current Python is|running on) Python ([\d.]+)",
            re.IGNORECASE,
        ),
        diagnosis="The package requires a newer Python version than the one active in the build environment.",
        suggestion={
            "action": "update",
            "path": "context.python_min",
            "value": "PLACEHOLDER",
            "comment": "Update python_min in the recipe context to match the package's python_requires.",
        },
    ),

    # -----------------------------------------------------------------------
    # CATEGORY: RATTLER_SCHEMA
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="RATTLER_YAML_PARSE_ERROR",
        category="RATTLER_SCHEMA",
        regex=re.compile(
            r"(?:×\s*)?Parsing: an unspecified error occurred"
            r"|error: additional properties are not allowed"
            r"|Schema validation failed",
            re.IGNORECASE,
        ),
        diagnosis=(
            "rattler-build could not parse the recipe.yaml. "
            "The file has a schema violation — a missing required key, extra key, or wrong type."
        ),
        suggestion={
            "action": "informational",
            "comment": (
                "Validate recipe.yaml against the schema at "
                "https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json. "
                "Common causes: missing package.name/version, wrong key names, or mixed v0/v1 syntax."
            ),
        },
    ),
    ErrorPattern(
        name="RATTLER_VIRTUAL_PACKAGE_IN_RUN",
        category="RATTLER_SCHEMA",
        regex=re.compile(
            r"Could not parse version spec: invalid version tree.*Tag: __\w+"
            r"|virtual package `__\w+` in `run` requirements",
            re.IGNORECASE,
        ),
        diagnosis=(
            "A virtual package (e.g. __osx, __unix, __glibc) was placed in run requirements. "
            "Virtual packages must go in run_constrained, not run — placing them in run crashes rattler-build 0.32+."
        ),
        suggestion={
            "action": "informational",
            "comment": (
                "Move virtual packages (e.g. __osx >=26) from requirements.run to requirements.run_constrained."
            ),
        },
    ),
    ErrorPattern(
        name="RATTLER_SELECTOR_SYNTAX_ERROR",
        category="RATTLER_SCHEMA",
        regex=re.compile(
            r"error.*evaluating selector expression"
            r"|unrecognized selector.*\[.*\]"
            r"|SelectorConfig.*unknown variable",
            re.IGNORECASE,
        ),
        diagnosis="A selector expression in recipe.yaml references an unknown variable or uses incorrect syntax.",
        suggestion={
            "action": "informational",
            "comment": (
                "In recipe.yaml (v1), use 'if/then/else' or skip list syntax. "
                "Comment-bracket selectors like '# [win]' are only valid in meta.yaml (v0). "
                "Available context variables: linux, osx, win, unix, aarch64, x86_64."
            ),
        },
    ),

    # -----------------------------------------------------------------------
    # CATEGORY: RUST
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="CARGO_BUILD_SCRIPT_FAILED",
        category="RUST",
        regex=re.compile(
            r"error: failed to run custom build command for `([\w-]+)`",
            re.IGNORECASE,
        ),
        diagnosis=(
            "A Rust crate's build script failed. Common causes: missing pkg-config, "
            "OpenSSL headers, or cmake not in the build environment."
        ),
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "pkg-config",
            "comment": (
                "Add pkg-config to build requirements. "
                "For openssl-sys, also add openssl to host and set "
                "OPENSSL_DIR=$PREFIX in the build script."
            ),
        },
    ),
    ErrorPattern(
        name="CARGO_OPENSSL_NOT_FOUND",
        category="RUST",
        regex=re.compile(
            r"Could not find directory of OpenSSL installation"
            r"|Could not find OpenSSL via pkg-config"
            r"|No package 'openssl' found",
            re.IGNORECASE,
        ),
        diagnosis="Rust crate openssl-sys could not locate the OpenSSL libraries.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.host",
            "value": "openssl",
            "comment": (
                "Add openssl to host requirements. "
                "Add to build.sh: export OPENSSL_DIR=$PREFIX and export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig."
            ),
        },
    ),
    ErrorPattern(
        name="RUST_LINKER_FAILED",
        category="RUST",
        regex=re.compile(
            r"error: linking with `[\w-]+-(?:cc|gcc|ld)`? failed: exit (?:code|status): \d+",
            re.IGNORECASE,
        ),
        diagnosis=(
            "Cargo's final link step failed. The conda cross-compiler linker was invoked "
            "but could not find a required system library."
        ),
        suggestion={
            "action": "set_env",
            "key": "RUSTFLAGS",
            "value": '"-C link-search=$PREFIX/lib"',
            "comment": (
                "Add RUSTFLAGS to build script to help the linker find conda-prefix libraries. "
                "Also ensure any C library dependencies are in host requirements."
            ),
        },
    ),

    # -----------------------------------------------------------------------
    # CATEGORY: NODE
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="NODE_GYP_FAILURE",
        category="NODE",
        regex=re.compile(r"gyp ERR! build error|gyp ERR! stack Error", re.IGNORECASE),
        diagnosis=(
            "node-gyp failed to build a native Node.js addon. "
            "This usually means Python 2/3 mismatch or missing C++ compiler."
        ),
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "${{ compiler('cxx') }}",
            "comment": (
                "Add ${{ compiler('cxx') }} to build requirements. "
                "Set npm_config_python=$PYTHON in build.sh if node-gyp is using the wrong Python."
            ),
        },
    ),
    ErrorPattern(
        name="NODE_ENGINE_INCOMPATIBLE",
        category="NODE",
        regex=re.compile(
            r"The engine 'node' is incompatible with this module\."
            r" Expected version '([^']+)'\. Got '([\d.]+)'",
            re.IGNORECASE,
        ),
        diagnosis="The Node.js version in the build environment does not satisfy the package's engine requirement.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "nodejs >=PLACEHOLDER",
            "comment": "Pin nodejs in build requirements to a version satisfying the engine constraint.",
        },
    ),

    # -----------------------------------------------------------------------
    # CATEGORY: SOURCE
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="SHA256_MISMATCH",
        category="SOURCE",
        regex=re.compile(
            r"(?:ChecksumMismatchError|sha256 mismatch|Hash mismatch|MD5 sums? mismatch)"
            r".*(?:expected|got|actual)?:?\s*([0-9a-f]{40,64})?",
            re.IGNORECASE,
        ),
        diagnosis=(
            "The downloaded source archive's checksum does not match the recipe's sha256. "
            "Either the upstream archive changed or the recipe has a wrong hash."
        ),
        suggestion={
            "action": "informational",
            "comment": (
                "Re-download the source and recalculate the hash: "
                "curl -L <url> | sha256sum. "
                "Use edit_recipe with action=calculate_hash to update automatically."
            ),
        },
    ),
    ErrorPattern(
        name="DOWNLOAD_FAILED",
        category="SOURCE",
        regex=re.compile(
            r"(?:Failed to download|ConnectionError|requests\.exceptions\."
            r"|Could not fetch|HTTPError: 4\d\d|No such file or directory.*\.tar\.)",
            re.IGNORECASE,
        ),
        diagnosis="The source archive could not be downloaded. The URL may be wrong, the release may not exist, or there is a network issue.",
        suggestion={
            "action": "informational",
            "comment": (
                "Verify the source URL resolves and the version exists on PyPI/GitHub. "
                "Check that the context.version in the recipe matches an actual published release."
            ),
        },
    ),

    # -----------------------------------------------------------------------
    # CATEGORY: SYSTEM
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="DISK_SPACE_EXHAUSTED",
        category="SYSTEM",
        regex=re.compile(
            r"No space left on device|OSError(?:\(\s*28\s*,\s*'No space left on device'\))|Disk quota exceeded",
            re.IGNORECASE,
        ),
        diagnosis="The build ran out of disk space.",
        suggestion={
            "action": "informational",
            "comment": (
                "Free disk space: run 'conda clean --all' and 'docker system prune' if using Docker builds. "
                "Set CONDA_BLD_PATH to a partition with more space."
            ),
        },
    ),
    ErrorPattern(
        name="PERMISSION_DENIED_BUILD",
        category="SYSTEM",
        regex=re.compile(
            r"(?:PermissionError|OSError).*\[Errno 13\] Permission denied"
            r"|Permission denied: '[^']*(?:conda|pkgs|envs)[^']*'",
            re.IGNORECASE,
        ),
        diagnosis="A build operation was denied due to insufficient filesystem permissions.",
        suggestion={
            "action": "informational",
            "comment": (
                "Ensure CONDA_BLD_PATH points to a directory writable by the current user. "
                "Do not use 'sudo' in build scripts."
            ),
        },
    ),

    # -----------------------------------------------------------------------
    # CATEGORY: TEST_FAILURE
    # -----------------------------------------------------------------------
    ErrorPattern(
        name="PYTEST_ASSERTION_FAILED",
        category="TEST_FAILURE",
        regex=re.compile(
            r"FAILED ([\w/.-]+\.py)::([\w:_]+) - ([\w.]+(?:Error|Exception|AssertionError))",
            re.IGNORECASE,
        ),
        diagnosis="A pytest test assertion failed during the conda-build test phase.",
        suggestion={
            "action": "informational",
            "comment": (
                "Run the tests locally to reproduce. "
                "If the test requires network access or external services, "
                "add a pytest marker and skip those tests in the conda test command."
            ),
        },
    ),
    ErrorPattern(
        name="TEST_PACKAGE_MISSING_IMPORT",
        category="TEST_FAILURE",
        regex=re.compile(
            r"ImportError while importing test module '([^']+)'",
            re.IGNORECASE,
        ),
        diagnosis="pytest could not import a test module, likely due to a missing test dependency.",
        suggestion={
            "action": "add_to_list",
            "path": "tests[0].requirements.run",
            "value": "pytest",
            "comment": "Ensure pytest and all test dependencies are listed in the test requirements block.",
        },
    ),
]


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

def _enrich_suggestion(pattern: ErrorPattern, match: re.Match[str]) -> dict[str, Any]:
    """Fill in PLACEHOLDER values from regex capture groups where possible."""
    suggestion = pattern.suggestion.copy()

    if pattern.name == "CMAKE_FIND_PACKAGE_ERROR":
        try:
            suggestion["value"] = match.group(1).lower()
        except IndexError:
            pass

    elif pattern.name == "MISSING_HEADER_FILE":
        suggestion["value"] = f"# TODO: conda package providing <{match.group(1)}>"

    elif pattern.name in ("UNDEFINED_LINKER_REFERENCE", "LINKER_CANNOT_FIND_LIBRARY"):
        lib = match.group(1)
        suggestion["value"] = f"# TODO: conda package providing lib{lib}"

    elif pattern.name == "MISSING_SHARED_LIBRARY_AT_RUNTIME":
        soname = match.group(1)  # e.g. libarchive.so.13
        lib_base = soname.split(".so")[0].lstrip("lib")
        suggestion["value"] = f"# TODO: conda package providing {soname} (try: lib{lib_base})"

    elif pattern.name == "MACOS_DYLIB_NOT_LOADED":
        dylib = match.group(1)
        lib_base = dylib.split(".")[0].lstrip("lib")
        suggestion["value"] = f"# TODO: conda package providing {dylib} (try: lib{lib_base})"

    elif pattern.name == "MODULE_NOT_FOUND_AT_TEST":
        module = match.group(1).split(".")[0]
        suggestion["value"] = module

    elif pattern.name == "CARGO_BUILD_SCRIPT_FAILED":
        crate = match.group(1)
        suggestion["comment"] = (
            f"The '{crate}' build script failed. "
            + suggestion.get("comment", "")
        )

    elif pattern.name == "NODE_ENGINE_INCOMPATIBLE":
        required = match.group(1).lstrip(">=^~").split(" ")[0]
        suggestion["value"] = suggestion["value"].replace("PLACEHOLDER", required)

    elif pattern.name == "INCORRECT_CPP_STANDARD":
        required = match.group(1)  # e.g. "17"
        suggestion["value"] = required

    elif pattern.name == "PYTHON_REQUIRES_NEWER":
        required = match.group(1)
        suggestion["value"] = required

    return suggestion


def analyze_log(error_log: str) -> list[dict[str, Any]]:
    """
    Scan the log against all known patterns.
    Returns a list of matches ordered by first appearance in the log.
    Each entry has: error_class, category, diagnosis, matched_text, match_position, suggestion.
    """
    hits: list[tuple[int, dict[str, Any]]] = []
    seen_classes: set[str] = set()

    for pattern in ERROR_LIBRARY:
        match = pattern.regex.search(error_log)
        if match and pattern.name not in seen_classes:
            seen_classes.add(pattern.name)
            hits.append((
                match.start(),
                {
                    "error_class": pattern.name,
                    "category": pattern.category,
                    "diagnosis": pattern.diagnosis,
                    "matched_text": match.group(0),
                    "suggestion": _enrich_suggestion(pattern, match),
                },
            ))

    # Sort by position in log so primary diagnosis is the earliest error
    hits.sort(key=lambda x: x[0])
    return [h for _, h in hits]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a conda-forge build failure log and suggest structured fixes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Pass '-' as logfile to read from stdin (used by the MCP server).\n"
            "Exit code 0 = at least one pattern matched; 1 = no match or error."
        ),
    )
    parser.add_argument(
        "logfile",
        type=Path,
        help="Path to the build error log file, or '-' to read from stdin.",
    )
    parser.add_argument(
        "--first-only",
        action="store_true",
        help="Return only the first (earliest) match instead of all matches.",
    )
    args = parser.parse_args()

    if str(args.logfile) == "-":
        error_log = sys.stdin.read()
    else:
        if not args.logfile.exists():
            print(json.dumps({"success": False, "error": f"Log file not found: {args.logfile}"}))
            sys.exit(1)
        error_log = args.logfile.read_text(encoding="utf-8", errors="replace")

    matches = analyze_log(error_log)

    if not matches:
        print(json.dumps({
            "success": False,
            "error": "No known error pattern matched. Manual inspection required.",
            "hint": f"ERROR_LIBRARY contains {len(ERROR_LIBRARY)} patterns across categories: "
                    + ", ".join(sorted({p.category for p in ERROR_LIBRARY})),
        }))
        sys.exit(1)

    if args.first_only:
        primary = matches[0]
        print(json.dumps({"success": True, **primary}, indent=2))
    else:
        primary = matches[0]
        print(json.dumps({
            "success": True,
            "match_count": len(matches),
            # Top-level fields mirror the primary match for backward compatibility
            "error_class": primary["error_class"],
            "category": primary["category"],
            "diagnosis": primary["diagnosis"],
            "matched_text": primary["matched_text"],
            "suggestion": primary["suggestion"],
            # Full list for multi-root-cause analysis
            "all_matches": matches,
        }, indent=2))

    sys.exit(0)


if __name__ == "__main__":
    main()
