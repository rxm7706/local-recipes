"""Chrome originating form for inline 422 mapping (FR-28, BS-7)."""

from __future__ import annotations

from django import forms


class VersionForm(forms.Form):
    """Bound surface FastAPI would reject with ``loc: ["body", "version"]``."""

    version = forms.CharField(required=False)
