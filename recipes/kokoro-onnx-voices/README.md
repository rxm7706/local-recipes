# kokoro-onnx-voices

The Kokoro v1.0 packed voice embeddings (`voices-v1.0.bin`), installed into the
conda prefix, plus the resolver module the whole chain uses:

```python
from kokoro_onnx import Kokoro
from kokoro_onnx_models import get_model_path, get_voices_path

kokoro = Kokoro(get_model_path(), get_voices_path())
```

Voices are shared by every model variant, so they ship here once. Install a
model alongside:

| package | variant | size | file |
|---|---|---|---|
| `kokoro-onnx-models` | f32 | 311 MB | `kokoro-v1.0.onnx` |
| `kokoro-onnx-models-fp16` | fp16 | 169 MB | `kokoro-v1.0.fp16.onnx` |
| `kokoro-onnx-models-int8` | int8 | 88 MB | `kokoro-v1.0.int8.onnx` |

They co-install. `get_model_path()` with no argument picks the
highest-precision one present; `get_model_path("int8")` selects explicitly, and
`list_variants()` reports what is actually installed.

Everything lands in `$CONDA_PREFIX/share/kokoro-onnx/`.
