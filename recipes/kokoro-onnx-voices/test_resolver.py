"""Resolver behaviour with voices installed but NO model package.

This is the state anyone who installs kokoro-onnx-voices on its own is in, and
the two failure modes worth guarding are both silent:

  * get_model_path() handing back a path to a file that is not there, so the
    error surfaces much later inside onnxruntime as an unreadable-file crash;
  * an unknown variant name being reported as "not installed" rather than as a
    typo, sending the caller off to install a package that does not exist.

Kept as a file rather than inline `python -c` lines: a multi-line double-quoted
YAML scalar folds its newlines into spaces, which would flatten the try/except
blocks below into a syntax error.
"""

import os
import sys

import numpy

import kokoro_onnx_models as m

# Voices resolve, live under this interpreter's prefix, and are intact.
voices = m.get_voices_path()
print("voices:", voices)
assert voices.startswith(sys.prefix), (voices, sys.prefix)
size = os.path.getsize(voices)
assert size == 28214398, size
print("voices bytes OK:", size)

data = numpy.load(voices)
assert len(data.files) > 1, data.files
print("voices load OK, speakers:", len(data.files))

# No model package is installed in this test environment.
assert m.list_variants() == [], m.list_variants()
print("no variants installed, as expected")

try:
    m.get_model_path()
except RuntimeError as exc:
    assert "kokoro-onnx-models" in str(exc), exc
    print("missing-model error OK:", exc)
else:
    raise AssertionError("get_model_path() should raise with no model installed")

# A named-but-absent variant is also a RuntimeError, and must say which.
try:
    m.get_model_path("int8")
except RuntimeError as exc:
    assert "int8" in str(exc), exc
    print("absent-variant error OK:", exc)
else:
    raise AssertionError("get_model_path('int8') should raise with no model installed")

# A typo is a ValueError, NOT a RuntimeError -- different problem, different fix.
try:
    m.get_model_path("bf16")
except ValueError as exc:
    print("unknown-variant error OK:", exc)
else:
    raise AssertionError("get_model_path('bf16') should raise ValueError")

# The documented alias resolves to fp16 rather than being rejected as unknown.
try:
    m.get_model_path("fp16-gpu")
except RuntimeError as exc:
    assert "fp16" in str(exc), exc
    print("fp16-gpu alias OK (maps to fp16):", exc)
else:
    raise AssertionError("fp16-gpu should reach the fp16 lookup and find it absent")

print("resolver OK")
