"""espeakng_loader — conda-native resolver for the eSpeak NG shared library.

Upstream's PyPI ``espeakng-loader`` bundles its own prebuilt libespeak-ng and
returns paths INSIDE the installed Python package. Those wheels are unusable:
the bundled library has its data directory compiled in as the upstream CI
machine's build tree (``/home/runner/work/espeakng-loader/...``), and nothing
overrides it -- not ``phonemizer``'s ``EspeakWrapper.set_data_path()``, not the
``ESPEAK_DATA_PATH`` environment variable. Verified 2026-09-07: a stock
``pip install kokoro-onnx`` aborts with
``Error processing file '/home/runner/.../phontab'`` on Python 3.12 and 3.14
alike.

This build keeps the upstream PUBLIC API byte-for-byte compatible -- the four
functions below are what ``kokoro-onnx`` and friends call -- but resolves them
to the ``espeak-ng`` conda package in the active prefix instead of a vendored
copy. That is the whole point: the conda build of espeak-ng records its data
path in ``info/has_prefix``, so conda rewrites it to the real environment at
install time, which is exactly the relocation mechanism the wheel lacks.

Consequences worth knowing:

* ``espeak-ng`` is a hard run dependency; this package ships no binaries.
* Paths follow the ACTIVE prefix (``sys.prefix``), so the same code works in
  every environment without reinstallation, and in an air-gapped one.
* ``CONDA_PREFIX`` is deliberately NOT consulted: it describes the shell's
  activated environment, which is not necessarily the interpreter running
  this code (``/path/to/env/bin/python`` invoked directly, a subprocess, a
  Jupyter kernel from another env). ``sys.prefix`` always describes the
  interpreter that imported this module.
"""

from __future__ import annotations

import ctypes
import os
import platform
import sys
from pathlib import Path

__all__ = [
    "get_library_path",
    "get_data_path",
    "load_library",
    "make_library_available",
]

__version__ = "0.2.4"


def _prefix() -> Path:
    return Path(sys.prefix)


def _lib_filename() -> str:
    system = platform.system()
    if system == "Windows":
        return "espeak-ng.dll"
    if system == "Darwin":
        return "libespeak-ng.dylib"
    return "libespeak-ng.so"


def get_library_path() -> str:
    """Absolute path to the eSpeak NG shared library in this prefix."""
    name = _lib_filename()
    # Windows conda layout puts DLLs under Library/bin; unix uses lib/.
    candidates = (
        [_prefix() / "Library" / "bin" / name, _prefix() / "bin" / name]
        if platform.system() == "Windows"
        else [_prefix() / "lib" / name]
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    # Return the conventional location even when missing: callers such as
    # kokoro-onnx probe with ctypes and fall back to a system-wide library,
    # and they need a path string rather than an exception to do that.
    return str(candidates[0])


def get_data_path() -> str:
    """Absolute path to espeak-ng-data in this prefix.

    Raises RuntimeError when absent, matching upstream's contract -- a missing
    data directory is the failure this whole package exists to prevent, so it
    is reported loudly rather than returned as a path that fails later inside
    the C library with a far less obvious message.
    """
    base = (
        _prefix() / "Library" / "share"
        if platform.system() == "Windows"
        else _prefix() / "share"
    )
    data_path = base / "espeak-ng-data"
    if not data_path.exists():
        raise RuntimeError(
            f"espeak-ng-data not found at {data_path}. "
            "Install the 'espeak-ng' conda package into this environment."
        )
    return str(data_path)


def load_library():
    """Load the shared library, or return None (upstream's behaviour)."""
    lib_path = get_library_path()
    try:
        return ctypes.CDLL(lib_path)
    except OSError as exc:
        print(f"Error loading shared library from {lib_path}: {exc}")
        return None


def make_library_available() -> None:
    """Put the library's directory on the platform's search path."""
    lib_dir = str(Path(get_library_path()).parent)
    system = platform.system()
    if system == "Windows":
        os.add_dll_directory(lib_dir)
    elif system == "Linux":
        os.environ["LD_LIBRARY_PATH"] = (
            lib_dir + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        )
    elif system == "Darwin":
        os.environ["DYLD_LIBRARY_PATH"] = (
            lib_dir + ":" + os.environ.get("DYLD_LIBRARY_PATH", "")
        )
    else:
        raise Exception(f"Unsupported platform: {system}")
