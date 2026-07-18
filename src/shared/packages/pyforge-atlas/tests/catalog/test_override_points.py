"""Gate check 5 (AC-4): endpoint-override accounting.

Exactly 20 `<HOST>_BASE_URL` override points — pinned as a 19-live +
1-reserved STRUCTURE (review-pass P7), never a bare 20 — survive as
dataset-level endpoint config, each env-var-overridable with a public
default. The A2-G2 extras, the fetcher URLs, and the paths section are
set-pinned separately; the total env-override surface is 31
(20 + 3 + 3 + 5, paths incl. the P9-added PYFORGE_ATLAS_DATA_ROOT).
"""

from __future__ import annotations

import re

from .conftest import (
    CATALOG_YML,
    EXPECTED_ENV_OVERRIDE_SURFACE,
    EXPECTED_EXTRA_OVERRIDES,
    EXPECTED_FETCHER_URLS,
    EXPECTED_LIVE_OVERRIDE_POINTS,
    EXPECTED_OVERRIDE_POINTS,
    PATHS_ENV_VARS,
    REPO_ROOT,
    RESERVED_OVERRIDE_POINTS,
    make_config_loader,
)

# P6: the default may not contain a comma — OmegaConf splits custom-resolver
# arguments on commas, so `${env_or:X,https://a,b}` would silently pass THREE
# arguments to the resolver (default truncated to "https://a"). The regex
# rejects commas (and stray braces) in the default explicitly so the hazard
# fails the gate instead of corrupting an endpoint at runtime.
_ENV_OR_RE = re.compile(r"^\$\{env_or:([A-Z0-9_]+),([^,{}]+)\}$")


def test_override_points_are_19_live_plus_1_reserved(globals_raw):
    """P7: assert the 19+1 structure, not a bare 20 — the reserved point
    (BASILISK_BASE_URL) has NO live helper behind it and must stay visibly
    reserved until B8 lands the nodes."""
    bases = set(globals_raw.get("endpoint_bases") or {})
    assert len(EXPECTED_LIVE_OVERRIDE_POINTS) == 19
    assert RESERVED_OVERRIDE_POINTS == {"BASILISK_BASE_URL"}
    assert bases == EXPECTED_LIVE_OVERRIDE_POINTS | RESERVED_OVERRIDE_POINTS
    assert len(bases) == 20  # 19 + 1, by the two set pins above


def test_extra_overrides_and_fetcher_urls_are_set_pinned(globals_raw):
    """P7: extras and fetcher URLs are exact-set-pinned like the bases."""
    assert set(globals_raw.get("extra_overrides") or {}) == EXPECTED_EXTRA_OVERRIDES
    assert set(globals_raw.get("fetcher_urls") or {}) == EXPECTED_FETCHER_URLS


def test_total_env_override_surface_is_pinned(globals_raw):
    """P7 accounting (adjusted +1 by P9's data_root): 20 + 3 + 3 + 5 = 31."""
    total = sum(
        len(globals_raw.get(section) or {})
        for section in ("endpoint_bases", "extra_overrides", "fetcher_urls", "paths")
    )
    assert total == EXPECTED_ENV_OVERRIDE_SURFACE


def test_each_override_point_is_env_overridable_with_default(globals_raw):
    bad = {}
    for section in ("endpoint_bases", "extra_overrides", "fetcher_urls"):
        for key, value in (globals_raw.get(section) or {}).items():
            m = _ENV_OR_RE.match(str(value))
            if not m or m.group(1) != key:
                bad[f"{section}.{key}"] = value
    assert not bad, (
        "override wiring violations (want ${env_or:<KEY>,<default>} with a "
        f"comma-free default — OmegaConf splits resolver args on commas): {bad}"
    )


def test_paths_are_env_overridable_with_the_declared_var_names(globals_raw):
    """P6/P9: the paths section follows the same env_or wiring, with an
    EXACT lowercase-key -> ENV_VAR map (incl. data_root, P9)."""
    paths = globals_raw.get("paths") or {}
    assert set(paths) == set(PATHS_ENV_VARS)
    bad = {}
    for key, value in paths.items():
        m = _ENV_OR_RE.match(str(value))
        if not m or m.group(1) != PATHS_ENV_VARS[key]:
            bad[f"paths.{key}"] = value
    assert not bad, f"paths wiring violations (want ${{env_or:<VAR>,<default>}}): {bad}"


def test_path_defaults_resolve_inside_the_repo_root(globals_raw):
    """P9: relative dataset paths resolve against the process CWD, and the
    documented invocation is the pixi task from the REPO ROOT — so every
    shipped default must stay inside the repo when resolved from there
    (the pre-review `../../../../` escapes silently depended on a
    member-dir CWD nobody uses). The seed root (git-tracked) must exist on
    disk; the `.claude/data/` stores are gitignored runtime state and may
    legitimately be absent in a fresh container, so they get the
    containment assertion only."""
    paths = globals_raw.get("paths") or {}
    # A plain-string path (no ${env_or:...} wrapper) is still a valid default —
    # fall back to the raw value so it gets containment-checked instead of
    # crashing on `None.group(2)` (Gemini PR-71).
    defaults = {}
    for key, value in paths.items():
        m = _ENV_OR_RE.match(str(value))
        defaults[key] = m.group(2) if m else str(value)
    escapees = {}
    for key, default in defaults.items():
        resolved = (REPO_ROOT / default).resolve()
        if not resolved.is_relative_to(REPO_ROOT):
            escapees[key] = str(resolved)
    assert not escapees, f"path defaults escape the repo root: {escapees}"
    # git-tracked seed root + the three seeds must exist here and now
    seed_root = (REPO_ROOT / defaults["seed_root"]).resolve()
    assert seed_root.is_dir(), f"seed_root default missing on disk: {seed_root}"
    for seed in ("lts-registry.yaml", "cwe_categories_seed.json", "spdx.schema.json"):
        assert (seed_root / seed).is_file(), f"seed file missing: {seed_root / seed}"


def test_anaconda_api_extra_override_survives(globals_raw, catalog_config):
    """Gap A2-G2: Phase F's ANACONDA_API_BASE_URL is current data access but
    NOT one of the 20 helper-backed points — asserted separately here, and it
    must actually back the core_anaconda_downloads_raw entry."""
    extras = globals_raw.get("extra_overrides") or {}
    assert "ANACONDA_API_BASE_URL" in extras
    # with no env override, the entry resolves to the public api.anaconda.org
    url = catalog_config["core_anaconda_downloads_raw"]["url"]
    assert url.startswith("https://api.anaconda.org")


_SCHEME_RE = re.compile(r"(?:https?|s3|gs|ftp)://", re.IGNORECASE)


def test_catalog_never_hardcodes_a_host(catalog_config):
    """AD-13 (tightened in review-pass P6): the REAL invariant is that every
    `url:` in catalog.yml routes through `${globals:` — plus a scheme scan
    (http/https/s3/gs/ftp) over the non-comment source lines so no literal
    endpoint of ANY scheme hides in values the url check does not reach."""
    raw_lines = CATALOG_YML.read_text(encoding="utf-8").splitlines()
    # Strip trailing inline comments before the scheme scan so a documentation
    # URL in a `# ...` note does not false-positive (Gemini PR-71).
    hardcoded = []
    for i, line in enumerate(raw_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        content = stripped.split(" #", 1)[0]
        if _SCHEME_RE.search(content):
            hardcoded.append((i + 1, stripped))
    assert not hardcoded, f"literal scheme://host in catalog.yml (non-comment): {hardcoded}"

    import yaml

    unresolved = yaml.safe_load("\n".join(raw_lines))
    bad_urls = {
        name: spec["url"]
        for name, spec in unresolved.items()
        if isinstance(spec, dict)
        and "url" in spec
        and not str(spec["url"]).startswith("${globals:")
    }
    assert not bad_urls, f"catalog url values must begin with ${{globals:...}}: {bad_urls}"


def test_env_override_reaches_resolved_catalog(monkeypatch):
    """End-to-end: an explicit env var beats the public default (spine
    Config row — os.environ.setdefault semantics)."""
    monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://mirror.corp/artifactory/conda-forge")
    loader = make_config_loader()
    url = dict(loader["catalog"])["core_repodata_raw"]["url"]
    assert url.startswith("https://mirror.corp/artifactory/conda-forge")


def test_empty_string_env_var_falls_back_to_default(monkeypatch):
    """P6: an empty-string env var is UNSET, not an empty endpoint base."""
    monkeypatch.setenv("CONDA_FORGE_BASE_URL", "")
    loader = make_config_loader()
    url = dict(loader["catalog"])["core_repodata_raw"]["url"]
    assert url.startswith("https://conda.anaconda.org/conda-forge")


def test_runtime_parameterized_entry_dataset(monkeypatch):
    """§ 3.4: user-supplied intake is an entry-scoped, runtime-parameterized
    dataset — `kedro run --params sbom_intake_path=...` re-points it."""
    loader = make_config_loader(runtime_params={"sbom_intake_path": "/tmp/my-intake.json"})
    assert dict(loader["catalog"])["sbom_intake_entry"]["filepath"] == "/tmp/my-intake.json"
