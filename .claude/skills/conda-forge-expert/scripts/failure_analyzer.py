#!/usr/bin/env python3
"""
Intelligent Build Failure Analyzer for conda-forge recipes.

This script takes an error log from a failed build, uses a library of
known error patterns to diagnose the root cause, and suggests a structured,
actionable fix.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Dict, Any, List, NamedTuple

class ErrorPattern(NamedTuple):
    """A known error pattern and its corresponding solution."""
    name: str
    regex: re.Pattern
    diagnosis: str
    suggestion: Dict[str, Any]

# A library of common, diagnosable build failures.
# This can be expanded over time.
ERROR_LIBRARY: List[ErrorPattern] = [
    ErrorPattern(
        name="COMPILER_NOT_FOUND",
        regex=re.compile(r"(gfortran|gcc|g\+\+|clang|cl\.exe|flang): (command not found|not recognized as an internal or external command)"),
        diagnosis="A required compiler (e.g., gfortran, gcc, clang) was not found in the build environment.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.build",
            "value": "{{ compiler('c') }}",
            "comment": "Add the appropriate C, C++, or Fortran compiler to the build requirements."
        }
    ),
    ErrorPattern(
        name="INCORRECT_CPP_STANDARD",
        regex=re.compile(r"error: (C\+\+\d{2}) is required but the CXX standard is (\d{2})"),
        diagnosis="The code requires a newer C++ standard than the one provided by the default compiler.",
        suggestion={
            "action": "add_to_cbc",
            "key": "cxx_compiler_version",
            "value": "17", # Default suggestion, can be improved
            "comment": "A conda_build_config.yaml file may be needed to specify the C++ standard, e.g., cxx_std: [17]"
        }
    ),
    ErrorPattern(
        name="CMAKE_FIND_PACKAGE_ERROR",
        regex=re.compile(r"CMake Error at .*:(find_package|find_dependency)\(\):\s+Could not find a package configuration file provided by \"(\w+)\""),
        diagnosis="CMake could not find a required dependency. The package is likely missing from the host requirements.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.host",
            "value": "dependency-to-add", # Placeholder
            "comment": "Add the missing CMake dependency (e.g., 'cmake', 'ninja', or the library itself) to the host requirements."
        }
    ),
    ErrorPattern(
        name="MISSING_HEADER_FILE",
        regex=re.compile(r"fatal error: '([^']+?)' file not found"),
        diagnosis="A header file is missing, which indicates a dependency is not installed in the build environment.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.host",
            "value": "dependency-providing-header", # Placeholder
            "comment": "Find which package provides the missing header and add it to the host requirements."
        }
    ),
    ErrorPattern(
        name="UNDEFINED_LINKER_REFERENCE",
        regex=re.compile(r"(undefined reference to|unresolved external symbol) `(.*?)'"),
        diagnosis="The linker could not find the implementation for a function or symbol, indicating a missing library.",
        suggestion={
            "action": "add_to_list",
            "path": "requirements.host",
            "value": "library-to-add", # Placeholder
            "comment": "A library is missing at link time. Add the package that provides the missing symbol to the host requirements."
        }
    ),
]

def analyze_log(error_log: str) -> Dict[str, Any] | None:
    """
    Analyzes an error log against the library of known patterns.
    Returns a structured diagnosis if a match is found, otherwise None.
    """
    for pattern in ERROR_LIBRARY:
        match = pattern.regex.search(error_log)
        if match:
            # Make the suggestion more specific if possible
            suggestion = pattern.suggestion.copy()
            if pattern.name == "CMAKE_FIND_PACKAGE_ERROR":
                suggestion["value"] = match.group(2).lower()
            elif pattern.name == "MISSING_HEADER_FILE":
                suggestion["value"] = f" # TODO: Find package for {match.group(1)}"
            
            return {
                "error_class": pattern.name,
                "diagnosis": pattern.diagnosis,
                "matched_text": match.group(0),
                "suggestion": suggestion,
            }
    return None

def main():
    parser = argparse.ArgumentParser(description="Analyze a build failure log and suggest a fix.")
    parser.add_argument(
        "logfile",
        type=Path,
        help="Path to the build error log file, or '-' to read from stdin."
    )
    
    args = parser.parse_args()

    if str(args.logfile) == "-":
        error_log = sys.stdin.read()
    else:
        if not args.logfile.exists():
            print(json.dumps({"success": False, "error": f"Log file not found: {args.logfile}"}))
            sys.exit(1)
        error_log = args.logfile.read_text()

    diagnosis = analyze_log(error_log)

    if diagnosis:
        print(json.dumps({"success": True, **diagnosis}, indent=2))
    else:
        print(json.dumps({"success": False, "error": "Could not identify a known error pattern."}))
        sys.exit(1)

if __name__ == "__main__":
    main()
