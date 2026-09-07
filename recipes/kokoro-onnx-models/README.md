# kokoro-onnx-models

The Kokoro v1.0 ONNX weights (f32) and packed voice embeddings, installed into
the conda prefix, plus a resolver module:

```python
from kokoro_onnx import Kokoro
from kokoro_onnx_models import get_model_path, get_voices_path

kokoro = Kokoro(get_model_path(), get_voices_path())
```

Files land in `$CONDA_PREFIX/share/kokoro-onnx/`.
