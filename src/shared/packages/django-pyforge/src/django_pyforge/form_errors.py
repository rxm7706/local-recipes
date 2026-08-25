"""Map FastAPI HTTP 422 JSON arrays onto Django form field errors (FR-28, BS-7).

``PydanticFormErrorBridge`` unpacks ``detail`` / ``loc`` into a
``ValidationError`` dict for inline HTMX highlighting. ``toast_http_422`` is
the naive dump: the same payload becomes an opaque blob and fields stay clean.
Do not add pydantic or django-htmx to pixi. Parse the JSON shape only.
"""

from __future__ import annotations

import json
from typing import Any

from django.forms import BaseForm
from django.forms import ValidationError
from django.forms.forms import NON_FIELD_ERRORS

_SKIP_LOC = frozenset({"body", "query", "path"})


def toast_http_422(payload: dict[str, Any]) -> str:
    """Opaque toast trap: dump the 422 JSON. Field errors are not produced."""
    return json.dumps(payload)


class PydanticFormErrorBridge:
    """Unpack HTTP 422 JSON error arrays into Django ``ValidationError`` dicts."""

    def to_validation_error(
        self,
        payload: dict[str, Any],
        *,
        field_names: frozenset[str] | None = None,
    ) -> ValidationError:
        detail = payload.get("detail")
        if not isinstance(detail, list):
            msg = detail if isinstance(detail, str) else toast_http_422(payload)
            return ValidationError({NON_FIELD_ERRORS: [str(msg)]})

        collected: dict[str, list[str]] = {}
        for item in detail:
            if not isinstance(item, dict):
                collected.setdefault(NON_FIELD_ERRORS, []).append(str(item))
                continue
            field = self._field_from_loc(item.get("loc"), field_names)
            msg = item.get("msg")
            collected.setdefault(field, []).append(str(msg) if msg else "Invalid")
        return ValidationError(collected)

    def apply(self, form: BaseForm, payload: dict[str, Any]) -> ValidationError:
        error = self.to_validation_error(payload, field_names=frozenset(form.fields))
        if not form.is_bound:
            msg = "PydanticFormErrorBridge.apply requires a bound form"
            raise ValueError(msg)
        if form._errors is None:
            form.full_clean()
        for field, messages in error.error_dict.items():
            target = None if field == NON_FIELD_ERRORS else field
            for message in messages:
                form.add_error(target, message)
        return error

    def _field_from_loc(
        self,
        loc: object,
        field_names: frozenset[str] | None,
    ) -> str:
        parts = loc if isinstance(loc, (list, tuple)) else ()
        names = [part for part in parts if isinstance(part, str) and part not in _SKIP_LOC]
        if field_names:
            for name in reversed(names):
                if name in field_names:
                    return name
        if names:
            return names[-1]
        return NON_FIELD_ERRORS
