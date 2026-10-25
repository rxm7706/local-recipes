"""``catalog_index`` pipeline -- every catalog entry's last write and row count on the data root (Story 37.10,
CAP-69). It reads what the other pipelines wrote, so it runs after them: ``pipeline_registry`` leaves it out of
``__default__``; run it with ``pyforge atlas run --pipelines catalog_index`` after a build, as the Pages job does.
"""

from .pipeline import create_pipeline

__all__ = ["create_pipeline"]
