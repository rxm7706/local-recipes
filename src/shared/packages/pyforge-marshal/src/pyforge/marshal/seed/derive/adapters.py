"""``seed/derive/adapters.py`` -- the one seam that composes the neutral
contract's shared fragments into the three whole-file agent-adapter files
(Story 11.1, epics AC "agent-adapter fan-out").

**The gap this closes.** ``templates/manifest.yaml`` has always declared
``cursor-rules`` (``.cursor/rules/specs.mdc``), ``gemini-md`` (``GEMINI.md``),
and ``copilot-instructions`` (``.github/copilot-instructions.md``) as
``generated-derived`` whole-file entries, but nothing ever supplied their
content -- ``verbs/adopt.py``'s own module docstring named this "known,
inherited limitation (1)": a real ``--apply`` against the packaged manifest
could only succeed for entries a later template-authoring story supplied
content for. This module is that story's content-authoring seam: it
composes the SAME three shared region fragments
(``templates/files/tiers.md.j2``, ``portability-contract.md.j2``,
``dream-first-workflow.md.j2``) that ``AGENTS.md``/``CLAUDE.md``'s own
``hybrid-managed-region`` bodies already render from (via ``verbs.adopt.
_region_body_from_template`` -- UNCHANGED, still the mechanism for those
two, see that module's own docstring) into a per-tool WHOLE FILE, wrapped in
a tool-specific framing template. One edit to a fragment changes all five
outputs' relevant content on the next render, because all five read the
identical file off disk at render time -- there is no cached or
hand-duplicated copy anywhere in this module or in ``verbs/adopt.py``.

**Why this module never calls ``engine.copier.materialize`` (confirmed
empirically, not merely by design preference).** The obvious alternative --
give each wrapper template its OWN ``.jinja``-suffixed file at its real
target-relative path inside the packaged ``seed/templates/`` tree (e.g.
``seed/templates/GEMINI.md.jinja``), and let ``verbs.adopt._materialized()``'s
existing lazy Copier render produce it for free -- was tried against the
REAL packaged manifest during this story's own development and fails
immediately: ``copier.run_copy`` stages the ENTIRE template tree, including
``manifest.yaml``, ``__init__.py``, and the six ``files/*.j2`` fragments
themselves (none of which correspond to any manifest entry's ``path``), and
``engine.copier.materialize``'s own ``_check_manifest_boundary`` refuses the
whole render as ``TemplateBoundaryError`` before any content is even
produced -- reproduced live:

    TemplateBoundaryError: materialize() staged path(s) outside the
    manifest boundary: __init__.py, files/bmad-multiproject.md.j2,
    files/dream-first-workflow.md.j2, files/model-badge.md.j2,
    files/model-ignores.gitignore.j2, files/portability-contract.md.j2,
    files/tiers.md.j2, manifest.yaml

Fixing that would mean adding manifest entries (or an exclude mechanism) for
Genesis's own packaging infrastructure files -- a change to
``engine/copier.py``'s boundary check, well outside this story's Code Map
and its "never touch ``seed/migrate/``, no new CLI verb" boundary. This
module therefore renders independently of Copier entirely: a plain,
self-contained read-fragments-then-substitute-into-a-wrapper composition,
invoked directly from ``verbs.adopt._default_commit``'s ``commit()``
dispatch for exactly the three ids ``ADAPTER_COMPOSITION`` names, bypassing
``_materialized()`` for them (every OTHER whole-file class -- ``bmad-switch``,
``bmad-loop-policy``, etc. -- is untouched and still routes through
``_materialized()``/``_staged_bytes_for`` as before).

**Why plain string substitution, not the ``jinja2`` library.** The Design
Notes this module was specced against offer both: "each wrapper does a
simple ``{% include %}`` OR string-embed of the corresponding fragment's
rendered body" (emphasis on the alternative). ``jinja2`` is only a
TRANSITIVE dependency here (via ``copier>=9.17,<10``, ``pyproject.toml``'s
own comment on that pin), never declared directly in
``[project.dependencies]`` -- and this story's own Boundaries forbid adding
a new third-party dep. A minimal, self-contained placeholder substitution
(``{{ name }}`` -> that fragment's raw text) needs no new dependency, no
autoescape/whitespace-control edge cases, and keeps this module
template-agnostic in the same spirit ``verbs.adopt._region_body_from_template``
already established for region bodies: read the fragment, splice it in
verbatim, never actually invoke a template engine on it.

**Data-driven adapter selection (no per-id branch).**
``model.manifest.ManifestEntry`` has no field to carry "which fragments and
wrapper template this entry composes from" (checked: neither ``pin`` nor any
other field fits, and adding one would touch ``model/manifest.py`` and the
schema outside this story's Code Map) -- so, per the Design Notes' own
fallback, ``ADAPTER_COMPOSITION`` is a small ``dict[str, AdapterSpec]`` table
here, keyed by the manifest's own ``id``. Adding a fifth adapter is one new
row in this table plus one new wrapper template file under ``templates/
files/`` -- ``render_adapter`` itself never branches on an adapter id."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from ..errors import InternalError
from ..regions.markers import REGION_NAME_PATTERN

# `{{ name }}` -- deliberately permissive on whitespace (`{{tiers}}` and
# `{{ tiers }}` both match) but NOT real Jinja: `name` is restricted to
# EXACTLY the alphabet a fragment/region name is already restricted to
# elsewhere in this package (`regions.markers.REGION_NAME_PATTERN`), so a
# wrapper template can never smuggle in arbitrary Python-adjacent syntax
# through this substitution, and so a digit-leading region/fragment name
# (legal under `REGION_NAME_PATTERN`, e.g. a hypothetical `9lives`) is
# still recognized rather than silently passing through un-substituted --
# built directly off `REGION_NAME_PATTERN.pattern`, not a hand-copied
# narrower alphabet, so the two can never drift apart again (review finding).
_PLACEHOLDER_RE = re.compile(r"\{\{\s*(" + REGION_NAME_PATTERN.pattern + r")\s*\}\}")


@dataclass(frozen=True)
class AdapterSpec:
    """Which shared region fragments compose one ``generated-derived``
    whole-file adapter's neutral-contract content, and which wrapper
    template embeds them with that adapter's own tool-specific framing.

    ``fragments`` names region/fragment ids exactly as ``templates/files/
    <id>.*.j2`` spells them (the same ids ``AGENTS.md``/``CLAUDE.md``'s own
    ``ManifestEntry.regions[].name`` values use) -- ``render_adapter`` reads
    each one directly off disk, verbatim, never a cached or duplicated copy.
    ``wrapper`` is a filename (not a path) resolved under the SAME
    ``templates/files/`` directory the fragments themselves live in."""

    fragments: tuple[str, ...]
    wrapper: str


# The three ids this story closes ("known, inherited limitation (1)" in
# `verbs/adopt.py`'s own module docstring) -- all three compose from the
# same three fragments as `AGENTS.md`'s own `agents-md` manifest entry
# (`tiers`, `portability-contract`, `dream-first-workflow`), each wrapped in
# its own tool-specific framing template. `CLAUDE.md`'s `claude-md` entry
# declares a DIFFERENT, narrower region set (`tiers`, `bmad-multiproject`) --
# out of scope here; only the three whole-file adapters are this table's
# concern.
ADAPTER_COMPOSITION: dict[str, AdapterSpec] = {
    "cursor-rules": AdapterSpec(
        fragments=("tiers", "portability-contract", "dream-first-workflow"),
        wrapper="cursor-rules.mdc.j2",
    ),
    "gemini-md": AdapterSpec(
        fragments=("tiers", "portability-contract", "dream-first-workflow"),
        wrapper="gemini-md.md.j2",
    ),
    "copilot-instructions": AdapterSpec(
        fragments=("tiers", "portability-contract", "dream-first-workflow"),
        wrapper="copilot-instructions.md.j2",
    ),
}


def _read_fragment(files_dir: Path, name: str) -> str:
    """The raw text of ``files_dir/<name>.*.j2`` -- tolerant of the ``.j2``
    suffix and of the fragment's own extension (``.md``/``.gitignore``/...),
    since only the NAME half before the first ``.`` identifies it (mirrors
    ``verbs.adopt._read_region_fragment``'s identical matching rule).

    Raises ``InternalError`` (a broken template installation, not a problem
    with the repository being adopted) naming ``name`` when no fragment
    matches, when MORE THAN ONE fragment matches (ambiguity refused loudly,
    matching this package's convention elsewhere), or when the matched
    fragment's own text contains ``{{`` -- fragments are read and spliced
    VERBATIM, never rendered, so un-rendered Jinja-shaped text reaching a
    real repo file would be a silent, hard-to-notice bug."""
    if files_dir.is_dir():
        matches = [
            candidate
            for candidate in sorted(files_dir.iterdir())
            if candidate.is_file() and candidate.name.removesuffix(".j2").split(".", 1)[0] == name
        ]
        if len(matches) > 1:
            raise InternalError(
                f"{len(matches)} files/{name}.*.j2 fragments found under {files_dir}:"
                f" {[candidate.name for candidate in matches]!r}",
                remedy=(
                    "the seed template tree ships more than one fragment for this name --"
                    " this is a broken template installation (ambiguous content), not a"
                    " problem with the repository being adopted"
                ),
            )
        if matches:
            text = matches[0].read_text(encoding="utf-8")
            if "{{" in text:
                raise InternalError(
                    f"files/{name}.*.j2 fragment contains Jinja syntax ('{{'), but adapter"
                    " composition reads fragments directly and splices them verbatim, never"
                    " renders them",
                    remedy=(
                        "remove the Jinja-shaped syntax from this fragment -- this is a broken"
                        " template installation, not a problem with the repository being"
                        " adopted"
                    ),
                )
            return text
    raise InternalError(
        f"no files/{name}.*.j2 fragment found under {files_dir}",
        remedy=(
            "verify the seed template tree provides a files/<name>.*.j2 fragment -- this is a"
            " broken template installation, not a problem with the repository being adopted"
        ),
    )


def _substitute(wrapper_text: str, fragments: Mapping[str, str], adapter_id: str) -> str:
    """``wrapper_text`` with every ``{{ name }}`` placeholder replaced by
    ``fragments[name]`` -- a single, non-recursive pass (``re.sub`` scans
    ``wrapper_text`` exactly once; a substituted fragment's own text, even if
    it somehow contained ``{{``, is never re-scanned for further
    placeholders, so this cannot loop or double-substitute).

    Raises ``InternalError`` naming ``adapter_id`` and the offending
    placeholder when the wrapper references a name not in ``fragments`` --
    a wrapper-authoring typo caught loudly at render time rather than
    silently left un-substituted in real output."""

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in fragments:
            raise InternalError(
                f"wrapper template for adapter {adapter_id!r} references unknown placeholder"
                f" {{{{ {name} }}}} -- expected one of {sorted(fragments)!r}",
                remedy=(
                    "fix the placeholder name in the wrapper template, or add the fragment to"
                    " this adapter's AdapterSpec.fragments -- this is a broken template"
                    " installation, not a problem with the repository being adopted"
                ),
            )
        return fragments[name]

    return _PLACEHOLDER_RE.sub(_replace, wrapper_text)


def _compose(files_dir: Path, adapter_id: str, spec: AdapterSpec) -> str:
    fragments = {name: _read_fragment(files_dir, name) for name in spec.fragments}
    wrapper_path = files_dir / spec.wrapper
    if not wrapper_path.is_file():
        raise InternalError(
            f"no wrapper template found at {wrapper_path} for adapter {adapter_id!r}",
            remedy=(
                f"add {spec.wrapper!r} under the seed template tree's files/ directory -- this"
                " is a broken template installation, not a problem with the repository being"
                " adopted"
            ),
        )
    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    return _substitute(wrapper_text, fragments, adapter_id)


def render_adapter(
    adapter_id: str,
    *,
    template_path: Path | str | None = None,
    composition: Mapping[str, AdapterSpec] | None = None,
) -> str:
    """The rendered whole-file content for ``adapter_id`` -- the shared
    region fragments its ``AdapterSpec`` names, read verbatim off disk and
    spliced into its wrapper template's own tool-specific framing.

    ``template_path`` -- ``None`` resolves to the in-package ``seed/
    templates/`` directory (mirrors ``verbs.adopt._region_body_from_template``'s
    identical seam, duplicated rather than imported -- this package's
    established "small deliberate duplication beats an import across a
    module boundary" trade, see ``verbs.adopt._read_text_or_blank``'s own
    docstring for the precedent); an explicit path lets a caller (a test, or
    a future caller with a custom template tree) supply a synthetic one.

    ``composition`` -- ``None`` (the default) uses this module's own
    ``ADAPTER_COMPOSITION``. A caller-supplied mapping is the extensibility
    seam the epics AC's "adding a fifth adapter needs no ``adapters.py``
    logic change" claim is tested against: a fifth adapter added purely via
    a new mapping entry (plus its wrapper template file) renders correctly
    with zero changes to this function's own code.

    Raises ``InternalError`` naming ``adapter_id`` when it has no entry in
    the composition table (an unknown adapter id, never silently skipped),
    and propagates ``_compose``'s own ``InternalError`` for a missing
    wrapper template, a missing/ambiguous fragment, an un-rendered
    Jinja-shaped fragment, or a wrapper template referencing an unknown
    ``{{ name }}`` placeholder (review finding: this fourth mode, raised by
    ``_substitute``, was previously undocumented here even though it is the
    one a wrapper-template author is most likely to actually hit).

    Deterministic: two calls with the same arguments produce byte-identical
    output -- every step is a plain file read plus string substitution, with
    no timestamp, random ordering, or external state involved."""
    table = composition if composition is not None else ADAPTER_COMPOSITION
    spec = table.get(adapter_id)
    if spec is None:
        raise InternalError(
            f"no wrapper-template composition registered for adapter {adapter_id!r}",
            remedy=(
                "add an AdapterSpec entry to ADAPTER_COMPOSITION naming which fragments and"
                " wrapper template compose this adapter's content"
            ),
        )
    if template_path is None:
        files_root = resources.files("pyforge.marshal.seed.templates") / "files"
        with resources.as_file(files_root) as real_files_dir:
            return _compose(real_files_dir, adapter_id, spec)
    return _compose(Path(template_path) / "files", adapter_id, spec)
