"""kokoro_onnx_models — locate Kokoro TTS weights inside the conda prefix.

``kokoro-onnx`` takes its model and voices as CONSTRUCTOR ARGUMENTS and reads
no environment variable for either (verified against 0.6.1: its only env
lookups are LOG_LEVEL, ONNX_PROVIDER and PHONEMIZER_ESPEAK_LIBRARY). A data
package therefore cannot make itself picked up implicitly the way
``playwright-browsers-base`` can -- the caller has to pass paths, and this
module exists to supply the right ones:

    from kokoro_onnx import Kokoro
    from kokoro_onnx_models import get_model_path, get_voices_path

    kokoro = Kokoro(get_model_path(), get_voices_path())

Model variants install as separate packages so you pay only for the one you
want, and they co-install because their filenames differ:

    kokoro-onnx-models        f32    311 MB   kokoro-v1.0.onnx
    kokoro-onnx-models-fp16   fp16   169 MB   kokoro-v1.0.fp16.onnx
    kokoro-onnx-models-int8   int8    88 MB   kokoro-v1.0.int8.onnx

``voices-v1.0.bin`` is shared by all of them and ships once, here.

Select explicitly with ``get_model_path("int8")``. With no argument the
highest-precision INSTALLED variant wins (f32 > fp16 > int8), so an
environment carrying only int8 still works without code changes.

Paths resolve from ``sys.prefix`` -- the interpreter actually running this
code -- rather than ``CONDA_PREFIX``, which describes the shell's activated
environment and need not be the same thing (a direct
``/path/to/env/bin/python`` call, a subprocess, a Jupyter kernel borrowed
from another environment).
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = [
    "VARIANTS",
    "get_data_dir",
    "get_model_path",
    "get_voices_path",
    "list_variants",
]

__version__ = "1.0"

VOICES_FILENAME = "voices-v1.0.bin"

#: Filename per variant, in descending precision -- the order used when no
#: variant is requested.
VARIANTS: dict[str, str] = {
    "f32": "kokoro-v1.0.onnx",
    "fp16": "kokoro-v1.0.fp16.onnx",
    "int8": "kokoro-v1.0.int8.onnx",
}

#: Upstream publishes `kokoro-v1.0.fp16-gpu.onnx` as a separate release asset,
#: but its bytes are IDENTICAL to `kokoro-v1.0.fp16.onnx` (sha256
#: c1610a859f3bdea01107e73e50100685af38fff88f5cd8e5c56df109ec880204, confirmed
#: by independent re-fetch 2026-09-07; the release notes describe only f32,
#: fp16 and int8). It is accepted as an alias rather than packaged twice --
#: shipping 169 MB of duplicate bytes would buy nothing.
_ALIASES = {"fp16-gpu": "fp16", "f16": "fp16", "float32": "f32", "float16": "fp16"}


def get_data_dir() -> Path:
    """Directory holding the Kokoro model files in this prefix."""
    return Path(sys.prefix) / "share" / "kokoro-onnx"


def list_variants() -> list[str]:
    """Variants actually installed here, in descending precision."""
    data = get_data_dir()
    return [v for v, fn in VARIANTS.items() if (data / fn).exists()]


def get_voices_path() -> str:
    """Absolute path to the packed voice embeddings."""
    path = get_data_dir() / VOICES_FILENAME
    if not path.exists():
        raise RuntimeError(
            f"{VOICES_FILENAME} not found at {path}. "
            "Install the 'kokoro-onnx-voices' conda package."
        )
    return str(path)


def get_model_path(variant: str | None = None) -> str:
    """Absolute path to a Kokoro ONNX model.

    variant: one of 'f32', 'fp16', 'int8' (or the aliases 'fp16-gpu', 'f16',
    'float32', 'float16'). None picks the highest-precision installed variant.
    """
    data = get_data_dir()
    if variant is None:
        available = list_variants()
        if not available:
            raise RuntimeError(
                f"No Kokoro model found in {data}. Install one of: "
                "kokoro-onnx-models (f32), kokoro-onnx-models-fp16, "
                "kokoro-onnx-models-int8."
            )
        variant = available[0]
    key = _ALIASES.get(variant, variant)
    if key not in VARIANTS:
        raise ValueError(
            f"Unknown variant {variant!r}. "
            f"Known: {sorted(VARIANTS)} (aliases: {sorted(_ALIASES)})."
        )
    path = data / VARIANTS[key]
    if not path.exists():
        installed = list_variants()
        raise RuntimeError(
            f"Variant {key!r} not installed (expected {path}). "
            f"Installed here: {installed or 'none'}."
        )
    return str(path)
