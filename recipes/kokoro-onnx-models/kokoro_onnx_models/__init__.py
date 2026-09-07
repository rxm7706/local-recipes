"""kokoro_onnx_models — locate the Kokoro TTS weights inside the conda prefix.

``kokoro-onnx`` takes its model and voices as CONSTRUCTOR ARGUMENTS and reads
no environment variable for either (verified against 0.6.1: the only env
lookups in the package are LOG_LEVEL, ONNX_PROVIDER and
PHONEMIZER_ESPEAK_LIBRARY). So a data package cannot make itself picked up
implicitly the way ``playwright-browsers-base`` can — the caller has to pass
paths, and this module exists to give them the right ones:

    from kokoro_onnx import Kokoro
    from kokoro_onnx_models import get_model_path, get_voices_path

    kokoro = Kokoro(get_model_path(), get_voices_path())
    samples, sample_rate = kokoro.create("Hello world", voice="af_sarah")

Paths resolve from ``sys.prefix`` — the interpreter actually running this
code — rather than ``CONDA_PREFIX``, which describes the shell's activated
environment and is not necessarily the same thing (a direct
``/path/to/env/bin/python`` call, a subprocess, a Jupyter kernel borrowed from
another environment).
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["get_data_dir", "get_model_path", "get_voices_path"]

__version__ = "1.0"

MODEL_FILENAME = "kokoro-v1.0.onnx"
VOICES_FILENAME = "voices-v1.0.bin"


def get_data_dir() -> Path:
    """Directory holding the Kokoro model files in this prefix."""
    return Path(sys.prefix) / "share" / "kokoro-onnx"


def _resolve(filename: str) -> str:
    path = get_data_dir() / filename
    if not path.exists():
        raise RuntimeError(
            f"{filename} not found at {path}. "
            "Install the 'kokoro-onnx-models' conda package into this "
            "environment."
        )
    return str(path)


def get_model_path() -> str:
    """Absolute path to the f32 Kokoro ONNX model."""
    return _resolve(MODEL_FILENAME)


def get_voices_path() -> str:
    """Absolute path to the packed voice embeddings."""
    return _resolve(VOICES_FILENAME)
