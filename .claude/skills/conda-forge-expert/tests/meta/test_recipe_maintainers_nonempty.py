"""Meta-test: every committed recipe declares at least one ``recipe-maintainers`` entry.

v8.86.1 — closes the repo-wide lint outage recorded in the v8.86.0 retro: an EMPTY
``extra.recipe-maintainers:`` (the key present, no list under it) crashes conda-smithy's
``lint_recipe_maintainers`` with ``TypeError: 'NoneType' object is not iterable``, and
because ``pixi run -e conda-smithy lint`` walks every recipe in one process, the crash
at the first offender (alphabetically ``recipes/Flake8-pyproject``) left every later
recipe unlinted. 16 recipes / 17 files carried the empty key (the 2026-08-20 inventory
commit ``d204da00fd`` stamped them without a maintainer).

Layer 3 of the same enforcement design as ``test_no_redundant_python_min.py``: the
generator writes ``- rxm7706`` for new recipes, the optimizer's MAINT-001 flags a
recipe with no maintainers, and this meta-test catches what survives into the
committed corpus so the repo-wide lint can never be silently truncated again.

Both formats are scanned. ``meta.yaml`` carries jinja so it is checked line-wise,
never via ``yaml.safe_load``; ``recipe.yaml`` gets the same line-wise scan so a
single code path covers the corpus. A maintainer list is non-empty when the key is
followed (ignoring blank and comment lines) by a ``- <handle>`` item at the key's indent or deeper
(YAML allows a block sequence at its parent key's indentation),
or when it carries an inline non-empty flow list (``[a, b]``).
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_RECIPES_DIR = _REPO_ROOT / "recipes"
_KEY_RE = re.compile(r"^(?P<indent>[ \t]*)recipe-maintainers:[ \t]*(?P<inline>\S.*)?$")
_ITEM_RE = re.compile(r"^[ \t]*-[ \t]*\S")


def _maintainers_nonempty(text: str) -> bool | None:
    """Return True/False for the first ``recipe-maintainers:`` key, or None when absent."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _KEY_RE.match(line)
        if not m:
            continue
        inline = (m.group("inline") or "").strip()
        if inline and not inline.startswith("#"):
            # Inline flow list: `recipe-maintainers: [a, b]` (non-empty) vs `[]`.
            return not re.fullmatch(r"\[\s*\]", inline.split("#", 1)[0].strip())
        key_indent = len(m.group("indent").expandtabs(4))
        for nxt in lines[i + 1:]:
            stripped = nxt.strip()
            if not stripped or stripped.startswith("#"):
                continue
            item_indent = len(nxt[: len(nxt) - len(nxt.lstrip())].expandtabs(4))
            return item_indent >= key_indent and bool(_ITEM_RE.match(nxt))
        return False
    return None


def _scan() -> tuple[list[str], list[str]]:
    empty: list[str] = []
    missing: list[str] = []
    for path in sorted(_RECIPES_DIR.glob("*/recipe.yaml")) + sorted(_RECIPES_DIR.glob("*/meta.yaml")):
        verdict = _maintainers_nonempty(path.read_text(encoding="utf-8", errors="replace"))
        rel = str(path.relative_to(_REPO_ROOT))
        if verdict is None:
            missing.append(rel)
        elif verdict is False:
            empty.append(rel)
    return empty, missing


def test_no_recipe_has_an_empty_recipe_maintainers_list() -> None:
    empty, _missing = _scan()
    assert not empty, (
        "recipe-maintainers: is present but EMPTY in these recipes -- conda-smithy's "
        "lint_recipe_maintainers crashes on None and the repo-wide `lint` task stops "
        "at the first one, leaving every later recipe unlinted. Add `- rxm7706`:\n  "
        + "\n  ".join(empty)
    )


def test_every_recipe_declares_recipe_maintainers() -> None:
    _empty, missing = _scan()
    assert not missing, (
        "no `recipe-maintainers:` key at all in these recipes (MAINT-001):\n  "
        + "\n  ".join(missing)
    )


def test_detector_distinguishes_the_three_shapes() -> None:
    assert _maintainers_nonempty("extra:\n  recipe-maintainers:\n    - rxm7706\n") is True
    assert _maintainers_nonempty("extra:\n  recipe-maintainers: [rxm7706]\n") is True
    assert _maintainers_nonempty("extra:\n  recipe-maintainers:\n\n#### CFE metadata\n  cfe-x: y\n") is False
    assert _maintainers_nonempty("extra:\n  recipe-maintainers:\n") is False
    assert _maintainers_nonempty("extra:\n  recipe-maintainers: []\n") is False
    assert _maintainers_nonempty("extra:\n  other: 1\n") is None
