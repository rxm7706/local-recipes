"""Gate check 5 (AC-4): endpoint-override accounting.

Exactly 22 `<HOST>_BASE_URL` override points — pinned as a 19-live +
1-reserved + 2-Story-21.4 STRUCTURE (review-pass P7, extended by Story
21.4), never a bare 22 — survive as dataset-level endpoint config, each
env-var-overridable with a public default. The A2-G2 extras, the fetcher
URLs, and the paths section are set-pinned separately; the total
env-override surface is 33 (22 + 3 + 3 + 5, paths incl. the P9-added
PYFORGE_ATLAS_DATA_ROOT).
"""

from __future__ import annotations

import re

from .conftest import (
    CATALOG_YML,
    DERIVED_STORE_PATHS,
    EXPECTED_ENV_OVERRIDE_SURFACE,
    EXPECTED_EXTRA_OVERRIDES,
    EXPECTED_FETCHER_URLS,
    EXPECTED_LIVE_OVERRIDE_POINTS,
    MEMBER_DIR,
    MEMBER_DIR_RELATIVE_PATHS,
    PATHS_ENV_VARS,
    REPO_ROOT,
    RESERVED_OVERRIDE_POINTS,
    STORY_21_4_OVERRIDE_POINTS,
    STORY_23_1_OVERRIDE_POINTS,
    make_config_loader,
)

# P6: the default may not contain a comma — OmegaConf splits custom-resolver
# arguments on commas, so `${env_or:X,https://a,b}` would silently pass THREE
# arguments to the resolver (default truncated to "https://a"). The regex
# rejects commas (and stray braces) in the default explicitly so the hazard
# fails the gate instead of corrupting an endpoint at runtime.
_ENV_OR_RE = re.compile(r"^\$\{env_or:([A-Z0-9_]+),([^,{}]+)\}$")


def test_override_points_are_19_live_plus_1_reserved_plus_2_story_21_4_plus_5_story_23_1(globals_raw):
    """P7: assert the 19+1+2+5 structure — the reserved point
    (BASILISK_BASE_URL) has NO live helper behind it and must stay visibly
    reserved; Story 21.4's 2 Tier-1 discovery points and Story 23.1's 5 Tier-3
    host bases are pinned by name inside the live set."""
    bases = set(globals_raw.get("endpoint_bases") or {})
    assert STORY_21_4_OVERRIDE_POINTS == {"ANACONDA_DIST_BASE_URL", "AOSS_PREMIUM_BASE_URL"}
    assert STORY_23_1_OVERRIDE_POINTS == {
        "HOMEBREW_BASE_URL",
        "NIXPKGS_BASE_URL",
        "SPACK_RAW_BASE_URL",
        "DEBIAN_BASE_URL",
        "FEDORA_SRC_BASE_URL",
    }
    assert STORY_21_4_OVERRIDE_POINTS <= EXPECTED_LIVE_OVERRIDE_POINTS
    assert STORY_23_1_OVERRIDE_POINTS <= EXPECTED_LIVE_OVERRIDE_POINTS
    assert len(EXPECTED_LIVE_OVERRIDE_POINTS - STORY_21_4_OVERRIDE_POINTS - STORY_23_1_OVERRIDE_POINTS) == 19
    assert len(EXPECTED_LIVE_OVERRIDE_POINTS) == 26
    assert RESERVED_OVERRIDE_POINTS == {"BASILISK_BASE_URL"}
    assert bases == EXPECTED_LIVE_OVERRIDE_POINTS | RESERVED_OVERRIDE_POINTS
    assert len(bases) == 27  # 19 + 2 + 5 + 1 reserved


def test_extra_overrides_and_fetcher_urls_are_set_pinned(globals_raw):
    """P7: extras and fetcher URLs are exact-set-pinned like the bases."""
    assert set(globals_raw.get("extra_overrides") or {}) == EXPECTED_EXTRA_OVERRIDES
    assert set(globals_raw.get("fetcher_urls") or {}) == EXPECTED_FETCHER_URLS


def test_total_env_override_surface_is_pinned(globals_raw):
    """P7 accounting (Story 23.1): 27 + 4 + 3 + 6 = 40."""
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
    """P6/P9: the two ROOT paths follow the env_or wiring, with an EXACT
    lowercase-key -> ENV_VAR map (incl. data_root, P9). Story 21.1: the
    three store paths are asserted separately (below) — they derive from
    `data_root` rather than carrying their own `env_or` wrapper, so the
    full `paths` section is PATHS_ENV_VARS | DERIVED_STORE_PATHS keys."""
    paths = globals_raw.get("paths") or {}
    assert set(paths) == set(PATHS_ENV_VARS) | set(DERIVED_STORE_PATHS)
    bad = {}
    for key, value in paths.items():
        if key in DERIVED_STORE_PATHS:
            continue
        m = _ENV_OR_RE.match(str(value))
        if not m or m.group(1) != PATHS_ENV_VARS[key]:
            bad[f"paths.{key}"] = value
    assert not bad, f"paths wiring violations (want ${{env_or:<VAR>,<default>}}): {bad}"


def test_store_paths_derive_from_data_root(globals_raw):
    """Story 21.1 (CAP-1): `vdb_store` / `osv_offline_store` / `pypi_conda_map`
    are plain `${paths.data_root}/<suffix>` self-references — no dedicated
    `env_or`-wrapped override of their own (PYFORGE_ATLAS_DATA_ROOT is the
    ONE override point for all three, per the spec's "Always" row)."""
    paths = globals_raw.get("paths") or {}
    bad = {}
    for key, suffix in DERIVED_STORE_PATHS.items():
        expected = f"${{paths.data_root}}/{suffix}"
        if str(paths.get(key)) != expected:
            bad[f"paths.{key}"] = paths.get(key)
    assert not bad, f"store paths must be '${{paths.data_root}}/<suffix>' literally: {bad}"


def test_store_paths_resolve_under_data_root(monkeypatch):
    """Story 21.1 AC: end-to-end (through the SAME `${globals:...}` resolver
    catalog.yml uses) the three store paths resolve under `data_root` — both
    the shipped default AND an explicit `PYFORGE_ATLAS_DATA_ROOT` override
    (the I/O matrix's "Env override" row: no hardcoded `.claude/data/` left
    in the resolved catalog)."""
    entries = {
        "vulnerability_vdb_store": "stores/vdb",
        "vulnerability_osv_offline_store": "stores/osv",
        "pypi_conda_map_store": "stores/pypi_conda_map.json",
    }

    loader = make_config_loader()
    catalog = dict(loader["catalog"])
    for entry, suffix in entries.items():
        assert catalog[entry]["filepath"] == f"data/{suffix}"

    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", "/tmp/atlas-catalog-check-override")
    loader = make_config_loader()
    catalog = dict(loader["catalog"])
    for entry, suffix in entries.items():
        assert catalog[entry]["filepath"] == f"/tmp/atlas-catalog-check-override/{suffix}"


def test_path_defaults_resolve_inside_the_repo_root(globals_raw):
    """P9, corrected by Story 21.8 (DW-FU-21-2): relative `filepath`/`path`
    catalog values are absolutized by Kedro's own
    ``_convert_paths_to_absolute_posix`` against `project_path` — the Kedro
    MEMBER dir (`src/shared/packages/pyforge-atlas`), which is also the pixi
    `cwd` `pyforge-atlas-bootstrap` actually runs `kedro run` from — never an
    assumed repo-root CWD. A live end-to-end bootstrap run (Story 21.8)
    proved the old REPO_ROOT-anchored premise false: it reproduced the exact
    `DatasetError` DW-FU-21-2 predicted for `seed_root`. Every shipped
    default must still stay inside the REPO as a whole once resolved from
    the member dir (a legitimate `../../../../` escape, like `seed_root`'s
    fix, is fine; escaping the repo entirely — e.g. a stray extra `../`
    reaching `/etc` — is not). The seed root (git-tracked) must exist on
    disk; the store defaults are gitignored runtime state and may
    legitimately be absent in a fresh container, so they get the
    containment assertion only."""
    paths = globals_raw.get("paths") or {}
    # A plain-string path (no ${env_or:...} wrapper) is still a valid default —
    # fall back to the raw value so it gets containment-checked instead of
    # crashing on `None.group(2)` (Gemini PR-71). Story 21.1: the three
    # DERIVED_STORE_PATHS keys are `${paths.data_root}/<suffix>` self-
    # references rather than `${env_or:...}` — substitute data_root's OWN
    # resolved default rather than containment-checking the literal
    # unresolved `${paths.data_root}` text (which would be vacuous: the
    # real end-to-end resolution is covered by
    # test_store_paths_resolve_under_data_root above).
    data_root_default = _ENV_OR_RE.match(str(paths["data_root"])).group(2)
    defaults = {}
    for key, value in paths.items():
        if key in DERIVED_STORE_PATHS:
            defaults[key] = f"{data_root_default}/{DERIVED_STORE_PATHS[key]}"
            continue
        m = _ENV_OR_RE.match(str(value))
        defaults[key] = m.group(2) if m else str(value)
    escapees = {}
    for key, default in defaults.items():
        # Story 21.6 (review finding, patch): local_recipes_dir's real consumer is
        # a live `kedro run`, which executes with cwd = the kedro project root
        # (MEMBER_DIR), not the repo root every other path here resolves against
        # (P9) — resolve it against the base its own real invocation actually
        # uses, still asserting the result lands inside the repo.
        base = MEMBER_DIR if key in MEMBER_DIR_RELATIVE_PATHS else REPO_ROOT
        resolved = (base / default).resolve()
        if not resolved.is_relative_to(REPO_ROOT):
            escapees[key] = str(resolved)
    assert not escapees, f"path defaults escape the repo root: {escapees}"
    # git-tracked seed root + the three seeds must exist here and now
    seed_root = (MEMBER_DIR / defaults["seed_root"]).resolve()
    assert seed_root.is_dir(), f"seed_root default missing on disk: {seed_root}"
    # Containment alone is not enough — a WRONG-but-still-contained path (e.g. the
    # original DW-FU-21-2 bug, which resolved one level short of the real seed dir
    # but still landed inside the repo) would pass the escapees check above and go
    # undetected. Pin the exact expected location too.
    expected_seed_root = (REPO_ROOT / ".claude/skills/conda-forge-expert/data").resolve()
    assert seed_root == expected_seed_root, f"seed_root resolved to {seed_root}, expected {expected_seed_root}"
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
        if isinstance(spec, dict) and "url" in spec and not str(spec["url"]).startswith("${globals:")
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
