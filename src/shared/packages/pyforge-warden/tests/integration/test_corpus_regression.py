"""Corpus-scale extraction regression gate (Story 5.2, NFR-R1/R2 at fleet
scale).

Iterates the full COMMITTED corpus (``tests/fixtures/corpus/`` — harvested
by ``scripts/harvest_corpus.py`` from this repo's own ~1,979
``recipe.yaml``/``meta.yaml`` recipes, plus the small pinned adversarial
set) directly through ``RecipeV1Extractor``/``MetaV0Extractor`` — no CLI, no
subprocess, pure Python — so this stays fast enough to live in the DEFAULT
``pyforge-warden-test`` suite (unlike ``test_extraction_oracle.py``'s
render-based oracle, which needs its own slower task; see that module's
updated docstring).

Two things are asserted per file:

* **0 uncaught exceptions.** ``UnparsableManifestError`` is the ONE typed,
  DESIGNED degrade-to-error outcome (``recipe_v1.py``/``meta_v0.py``'s own
  documented error taxonomy: a structurally corrupt document — duplicate
  YAML keys, an alias expansion, a multi-line ``{% set %}`` tag our
  regex-only neutralizer can't span, ...) — it is CAUGHT here, counted, and
  never re-raised: same as ``cli.py``'s own typed-error seam, this is
  "caught", not "uncaught". Any OTHER exception type escaping ``extract()``
  is a genuine internal-defect bug this corpus surfaced — the test fails
  loud, naming the file, and the fix belongs in the extractor, never a
  suppression here (Boundaries: "no production changes expected here unless
  the corpus surfaces a genuine uncaught-exception bug -- in which case: fix
  it, never suppress it"). Live-verified over the full corpus while
  authoring this story: 0 such bugs.
* **The ratcheted "unparseable rate".** Mirrors ``hygiene.py``'s
  ``UNPARSEABLE_RATE_BASELINE`` NFR-R2 pattern (first-measurement-sets-
  baseline, may only ever DECREASE), but at the extraction layer and corpus
  scale: the numerator is deliberately BROADER than the Code Map's original
  "files containing >=1 degraded component" wording alone — a whole-file
  ``UnparsableManifestError`` is a MORE severe failure to extract than a
  single degraded component, and a ratchet that only tracked the latter
  would blindly miss a regression that turned many more real recipes into
  manifest-level failures. ``CORPUS_UNPARSEABLE_RATE_BASELINE`` therefore
  counts a file as "unparseable" if EITHER ``extract()`` raised
  ``UnparsableManifestError`` OR it returned >=1 component whose
  ``extraction_mode`` is ``RAW_MALFORMED``/``NAME_ONLY`` (the E1 degrade
  ladder's two "something went badly enough to guess" tiers —
  ``UNION_MARKED`` is a clean, fully-resolved selector-union leaf, not a
  degrade, and is deliberately excluded). Measured this story:
  931/1987 files (~46.85%) — a real-world number, not a design target: this
  repo's own conda-forge recipes lean heavily on ``pin_compatible()``/
  ``compiler()``/expression-version Jinja the non-executing extractor
  correctly declines to guess at. The baseline exists to catch a
  REGRESSION (this rate creeping UP as new extractor code lands), not to
  chase it toward zero.

NFR-C1 (engine-version-range discipline) is deliberately NOT re-tested
here: it is already fully covered at both the unit level
(``tests/meta/test_engine_version_range_sync.py``, Story 6.6) and needs no
corpus-scale variant (an engine's ``--version`` output does not depend on
which project is being scanned) — citing that existing coverage rather than
duplicating it, per this story's Code Map.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.warden.discovery import META_YAML_KIND, RECIPE_YAML_KIND
from pyforge.warden.extract import UnparsableManifestError
from pyforge.warden.extract.meta_v0 import MetaV0Extractor
from pyforge.warden.extract.recipe_v1 import RecipeV1Extractor
from pyforge.warden.models import ExtractionMode, ScannedManifest
from pyforge.warden.routing import DefaultRouter

CORPUS_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "corpus"
RECIPES_DIR = CORPUS_DIR / "recipes"
ADVERSARIAL_DIR = CORPUS_DIR / "adversarial"

# A sanity floor, not the real expected count (~1,987 as of this story) --
# guards against an accidentally-emptied/partially-checked-out corpus
# silently passing every assertion below vacuously (0 files -> 0
# exceptions, 0/0 undefined-but-harmless rate).
_MINIMUM_EXPECTED_CORPUS_SIZE = 1900

# NFR-R2 ratchet (see module docstring for the exact numerator this
# measures): first value = what's empirically measured this story. For a
# given committed corpus it may only ever DECREASE -- raising it to absorb
# an extractor-code regression on an UNCHANGED corpus is the one forbidden
# move. A DELIBERATE corpus change (re-running scripts/harvest_corpus.py,
# growing the adversarial set) legitimately changes both sides of the
# fraction: re-measure and update this constant in the SAME PR that
# changes the corpus, citing the new measurement (follow-up review
# finding: the committed slack over the measured rate is deliberately
# ~0 files, so essentially ANY corpus change requires this re-measure).
CORPUS_UNPARSEABLE_RATE_BASELINE = 0.4686

_DEGRADED_MODES = (ExtractionMode.RAW_MALFORMED, ExtractionMode.NAME_ONLY)


def _corpus_files() -> list[tuple[Path, str]]:
    """Every ``recipe.yaml``/``meta.yaml`` under the committed corpus
    (``recipes/`` + BOTH adversarial subtrees), paired with its manifest
    kind -- a plain directory walk, not a fixture-by-fixture hardcoded list
    (the whole point of a corpus-scale gate)."""
    files: list[tuple[Path, str]] = []
    for path in sorted(CORPUS_DIR.rglob("recipe.yaml")):
        files.append((path, RECIPE_YAML_KIND))
    for path in sorted(CORPUS_DIR.rglob("meta.yaml")):
        files.append((path, META_YAML_KIND))
    return files


def test_corpus_is_provisioned():
    """A harvest sanity guard, not the real regression gate below -- an
    empty/partial corpus must fail LOUD here rather than let the real gate
    pass vacuously."""
    files = _corpus_files()
    assert len(files) >= _MINIMUM_EXPECTED_CORPUS_SIZE, (
        f"expected at least {_MINIMUM_EXPECTED_CORPUS_SIZE} corpus files, "
        f"found {len(files)} -- run scripts/harvest_corpus.py"
    )
    assert RECIPES_DIR.is_dir()
    assert ADVERSARIAL_DIR.is_dir()


def test_corpus_extraction_never_raises_uncaught_and_holds_the_unparseable_rate_baseline():
    router = DefaultRouter()
    recipe_extractor = RecipeV1Extractor(router)
    meta_extractor = MetaV0Extractor(router)

    files = _corpus_files()
    assert len(files) >= _MINIMUM_EXPECTED_CORPUS_SIZE

    uncaught: list[str] = []
    unparseable_count = 0
    degraded_count = 0

    for path, kind in files:
        extractor = recipe_extractor if kind == RECIPE_YAML_KIND else meta_extractor
        manifest = ScannedManifest(path=path.name, kind=kind)
        try:
            components = extractor.extract(path, manifest)
        except UnparsableManifestError:
            unparseable_count += 1
            continue
        except Exception as exc:  # noqa: BLE001 -- exactly what this gate hunts for
            uncaught.append(f"{path}: {exc.__class__.__name__}: {exc}")
            continue
        if any(c.extraction_mode in _DEGRADED_MODES for c in components):
            degraded_count += 1

    assert not uncaught, (
        f"{len(uncaught)} corpus file(s) raised an UNCAUGHT exception "
        f"(never UnparsableManifestError -- a genuine extractor bug):\n"
        + "\n".join(uncaught[:20])
    )

    rate = (degraded_count + unparseable_count) / len(files)
    assert rate <= CORPUS_UNPARSEABLE_RATE_BASELINE, (
        f"corpus unparseable rate regressed: {rate:.4f} "
        f"({degraded_count} degraded + {unparseable_count} unparsable of "
        f"{len(files)}) exceeds the committed baseline "
        f"{CORPUS_UNPARSEABLE_RATE_BASELINE}"
    )


def test_adversarial_set_degrades_gracefully_and_never_raises():
    """The I/O matrix's dedicated adversarial-file row: every file under
    ``adversarial/`` (upstream + hand-authored) must extract without
    raising ANYTHING -- not even ``UnparsableManifestError`` (unlike the
    real-recipe corpus above, where a structurally-broken real recipe is a
    legitimate, typed outcome, the adversarial set exists specifically to
    prove graceful component-level degradation, never a manifest-level
    failure)."""
    router = DefaultRouter()
    recipe_extractor = RecipeV1Extractor(router)
    meta_extractor = MetaV0Extractor(router)

    adversarial_files = [
        (path, RECIPE_YAML_KIND) for path in sorted(ADVERSARIAL_DIR.rglob("recipe.yaml"))
    ] + [(path, META_YAML_KIND) for path in sorted(ADVERSARIAL_DIR.rglob("meta.yaml"))]
    assert adversarial_files, "the adversarial set must not be empty"

    for path, kind in adversarial_files:
        extractor = recipe_extractor if kind == RECIPE_YAML_KIND else meta_extractor
        manifest = ScannedManifest(path=path.name, kind=kind)
        components = extractor.extract(path, manifest)  # must never raise
        assert components, f"{path} must contribute at least one component"
