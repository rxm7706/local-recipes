"""Story 15.3 — conda-installer backends for tea / cis / utility-skills /
manticore.

Each addition drives the package's own `*-install` entry point (AD-1),
records a `_bmad/custom/config.toml` `[modules.<name>]` manifest section
(Story 46.2, AD-9 -- moved off `_bmad/config.yaml`), refuses skill-name
collisions before first install, and stays reproducible against a
fresh-clone fixture (share data staged under `.pixi/envs/pyforge-guild`).
WDS is covered as an explicit skip citation, never as a registered module.

Story 46.3 adds TEA's own post-install flattening (`workflows/testarch/
bmad-testarch-*` -> ten top-level `.claude/skills/` entries) and the
module.yaml-answers mechanism (`test_artifacts` overridden, every other
TEA variable at its own declared default) -- `tea_fixture` below stages
the REAL nested share shape (`workflows/testarch/<leaf>/`, never a flat
`testarch/` leaf) plus a small representative `module.yaml`, and
`_fake_installer_run` copies whatever the installer's own upstream layout
puts directly under each source dir VERBATIM (a `flatten_nested_dirs`
container copied whole, un-flattened) so Steward's own post-install
flatten step under test has real work to do.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

from pyforge.steward.cli import EXIT_OK, main
from pyforge.steward.provision import (
    _SUPPORTED_MODULES,
    CondaInstallBackend,
    ProvisionDuty,
    SetupSkillBackend,
    _installer_skill_names,
    _manifest_location_label,
    _module_yaml_answers,
    provision_module,
)


def _full_namespace(**overrides):
    base = {
        "module": None,
        "env": None,
        "runner": None,
        "list": False,
        "verify": False,
        "list_modules": False,
        "json": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _stage_share_skills(
    root: Path,
    *,
    package: str,
    source_dir: str,
    skill_names: tuple[str, ...],
) -> Path:
    """Stage a minimal share/<package>/<source_dir>/<skill>/ tree under the
    fresh-clone pixi-env convention Story 6.1 already uses for bmb."""
    share = root / ".pixi/envs/pyforge-guild/share" / package / source_dir
    for name in skill_names:
        (share / name).mkdir(parents=True)
        (share / name / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    return share


def _stage_nested_share_skills(
    root: Path,
    *,
    package: str,
    source_dir: str,
    container: str,
    leaf_names: tuple[str, ...],
) -> Path:
    """Stage share/<package>/<source_dir>/<container>/<leaf>/ -- TEA's own
    real, one-level-too-deep `workflows/testarch/bmad-testarch-*` shape
    (Story 46.3), as opposed to `_stage_share_skills`'s flat leaf shape."""
    share = root / ".pixi/envs/pyforge-guild/share" / package / source_dir / container
    for name in leaf_names:
        (share / name).mkdir(parents=True)
        (share / name / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    return share


_TEA_WORKFLOW_LEAF_NAMES: tuple[str, ...] = (
    "bmad-teach-me-testing",
    "bmad-testarch-atdd",
    "bmad-testarch-automate",
    "bmad-testarch-ci",
    "bmad-testarch-framework",
    "bmad-testarch-nfr",
    "bmad-testarch-test-design",
    "bmad-testarch-test-review",
    "bmad-testarch-trace",
)
_TEA_ALL_SKILL_NAMES: frozenset[str] = frozenset({"bmad-tea", *_TEA_WORKFLOW_LEAF_NAMES})

# A small REPRESENTATIVE module.yaml -- not the full 14-variable real file
# (`.pixi/envs/pyforge-guild/share/bmad-method-test-architecture-enterprise/
# module.yaml`), just enough shape to exercise the override-one-key,
# keep-the-rest-at-default contract: a `test_artifacts` variable to
# override, a bool variable and a string variable that must both survive
# untouched, and a non-variable scalar (`code`) that must be skipped.
_TEA_MODULE_YAML_TEXT = (
    "code: tea\n"
    "test_artifacts:\n"
    '  prompt: "Where should test artifacts be stored?"\n'
    '  default: "{output_folder}/test-artifacts"\n'
    '  result: "{project-root}/{value}"\n'
    "tea_use_playwright_utils:\n"
    '  prompt: "Enable Playwright Utils integration?"\n'
    "  default: true\n"
    '  result: "{value}"\n'
    "ci_platform:\n"
    '  prompt: "Which CI/CD platform do you use?"\n'
    '  default: "auto"\n'
    '  result: "{value}"\n'
)


def _fake_installer_run(cmd, **kwargs):  # noqa: ARG001
    """Stand in for `bmad-*-install <dest>`: copies whatever the installer's
    own upstream layout puts directly under each `skill_source_dirs` entry
    VERBATIM -- for a `flatten_nested_dirs` source (TEA's own `workflows`),
    that is the CONTAINER (e.g. `testarch`), copied whole and un-flattened,
    exactly like the real `bmad-tea-install` does. Steward's own post-install
    `_flatten_nested_skill_dirs` step is what is under test here, never a
    fake that pre-flattens on the installer's behalf."""
    installer = Path(cmd[0]).name if cmd else ""
    dest = Path(cmd[1]) if len(cmd) > 1 else Path(".claude/skills")
    dest.mkdir(parents=True, exist_ok=True)

    # Map installer → backend from the live `_SUPPORTED_MODULES` registry so
    # the fake stays in sync.
    name = next(
        (
            key
            for key, backend in _SUPPORTED_MODULES.items()
            if isinstance(backend, CondaInstallBackend) and backend.installer == installer
        ),
        None,
    )
    assert name is not None, f"unexpected installer {installer!r}"
    backend = _SUPPORTED_MODULES[name]
    assert isinstance(backend, CondaInstallBackend)

    cwd = Path(kwargs.get("cwd") or ".")
    prefix = Path((kwargs.get("env") or {}).get("CONDA_PREFIX", cwd / ".pixi/envs/pyforge-guild"))
    share_root = prefix / "share" / backend.share_package

    def _copy_dir(src: Path, target: Path) -> None:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target)

    installed: list[str] = []
    if backend.skill_names:
        # cis: explicit allowlist, staged under skills/ (or a fallback
        # source dir) in fixtures even though the real package uses an
        # allowlist rather than directory discovery.
        for skill in backend.skill_names:
            src = share_root / "skills" / skill
            if not src.is_dir():
                for source in ("skills", *backend.skill_source_dirs):
                    candidate = share_root / source / skill
                    if candidate.is_dir():
                        src = candidate
                        break
            assert src.is_dir(), f"missing staged skill {skill}"
            _copy_dir(src, dest / skill)
            installed.append(skill)
    else:
        for source in backend.skill_source_dirs:
            directory = share_root / source
            if not directory.is_dir():
                continue
            for child in sorted(p for p in directory.iterdir() if p.is_dir()):
                _copy_dir(child, dest / child.name)
                installed.append(child.name)

    stdout = f"Installed {len(installed)} skill(s) to '{dest}':\n" + "".join(f"  - {s}\n" for s in installed)
    return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")


@pytest.fixture
def tea_fixture(tmp_path):
    _stage_share_skills(
        tmp_path,
        package="bmad-method-test-architecture-enterprise",
        source_dir="agents",
        skill_names=("bmad-tea",),
    )
    _stage_nested_share_skills(
        tmp_path,
        package="bmad-method-test-architecture-enterprise",
        source_dir="workflows",
        container="testarch",
        leaf_names=_TEA_WORKFLOW_LEAF_NAMES,
    )
    share_root = tmp_path / ".pixi/envs/pyforge-guild/share/bmad-method-test-architecture-enterprise"
    (share_root / "module.yaml").write_text(_TEA_MODULE_YAML_TEXT, encoding="utf-8")
    return tmp_path


@pytest.fixture
def cis_fixture(tmp_path):
    backend = _SUPPORTED_MODULES["cis"]
    assert isinstance(backend, CondaInstallBackend)
    _stage_share_skills(
        tmp_path,
        package=backend.share_package,
        source_dir="skills",
        skill_names=backend.skill_names,
    )
    return tmp_path


# ── Cross-module skill-name collision (registry integrity) ───────────────


def test_supported_installer_modules_have_disjoint_skill_names():
    """Skill-name-collision-checked at the registry: no two conda-install
    backends claim the same skill name."""
    claimed: dict[str, str] = {}
    for name, backend in _SUPPORTED_MODULES.items():
        if not isinstance(backend, CondaInstallBackend):
            continue
        names = backend.skill_names
        if not names:
            # Discovery backends (tea/utility/manticore) — use the live share
            # tree when the local-recipes env is present; otherwise skip the
            # dynamic half (explicit cis allowlist still checked above).
            continue
        for skill in names:
            assert skill not in claimed, f"skill {skill!r} claimed by both {claimed[skill]!r} and {name!r}"
            claimed[skill] = name


def test_live_share_skill_names_are_disjoint_across_installer_modules():
    """When the pixi local-recipes env is present, discovered skill names
    across tea/cis/utility-skills/manticore must not collide."""
    root = Path(__file__).resolve()
    repo = None
    for ancestor in root.parents:
        if (ancestor / "scripts/bmad-loop-worktree").is_file():
            repo = ancestor
            break
    assert repo is not None
    share = repo / ".pixi/envs/pyforge-guild/share"
    if not share.is_dir():
        pytest.skip("local-recipes pixi env share data not present")

    claimed: dict[str, str] = {}
    for name, backend in _SUPPORTED_MODULES.items():
        if not isinstance(backend, CondaInstallBackend):
            continue
        share_root = share / backend.share_package
        if not share_root.is_dir():
            pytest.skip(f"share package {backend.share_package} missing")
        for skill in _installer_skill_names(backend, share_root=share_root):
            assert skill not in claimed, f"skill {skill!r} claimed by both {claimed[skill]!r} and {name!r}"
            claimed[skill] = name
    assert claimed  # sanity: at least one skill discovered


_UTILITY_SKILLS_EXPECTED_NAMES: frozenset[str] = frozenset(
    {
        "bmad-os-audit-file-refs",
        "bmad-os-changelog",
        "bmad-os-changelog-social",
        "bmad-os-diataxis",
        "bmad-os-editorial-review-translation",
        "bmad-os-findings-triage",
        "bmad-os-gh-triage",
        "bmad-os-review-pr",
        "bmad-os-root-cause-analysis",
        "bmad-os-skill-to-bundle",
    }
)


def test_live_utility_skills_share_tree_matches_the_ten_expected_names():
    """DW-FU-15-3-4 (utility-skills half; the CIS half already closed by
    Story 46.8): the real installed `share/bmad-utility-skills/skills/`
    tree must discover exactly these 10 `bmad-os-*` names -- a share-tree
    change (a skill added or removed upstream) that isn't reflected here
    must fail this assertion loudly, rather than surfacing only as a
    post-install skills-missing `RuntimeError` at provision time."""
    root = Path(__file__).resolve()
    repo = None
    for ancestor in root.parents:
        if (ancestor / "scripts/bmad-loop-worktree").is_file():
            repo = ancestor
            break
    assert repo is not None
    share = repo / ".pixi/envs/pyforge-guild/share"
    if not share.is_dir():
        pytest.skip("local-recipes pixi env share data not present")

    backend = _SUPPORTED_MODULES["utility-skills"]
    assert isinstance(backend, CondaInstallBackend)
    share_root = share / backend.share_package
    if not share_root.is_dir():
        pytest.skip(f"share package {backend.share_package} missing")

    discovered = set(_installer_skill_names(backend, share_root=share_root))
    assert discovered == _UTILITY_SKILLS_EXPECTED_NAMES


# ── provision_module (installer backends) ────────────────────────────────


def test_provision_tea_via_installer_records_manifest_and_skills(tea_fixture, monkeypatch):
    """Story 46.3: the installer's own upstream layout lands `bmad-tea` +
    `testarch` (the one-level-too-deep container); post-flatten, ten
    top-level skill dirs exist and `testarch` itself does not survive."""
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    result = provision_module("tea", cwd=tea_fixture)

    assert result["installer"] == "bmad-tea-install"
    assert set(result["skills_installed"]) == _TEA_ALL_SKILL_NAMES
    for skill in _TEA_ALL_SKILL_NAMES:
        assert (tea_fixture / ".claude/skills" / skill).is_dir(), skill
    assert not (tea_fixture / ".claude/skills/testarch").exists()
    config = tomllib.loads((tea_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8"))
    assert "tea" in config["modules"]
    assert config["modules"]["tea"]["installer"] == "bmad-tea-install"
    assert config["modules"]["tea"]["provisioned_by"] == "steward"
    assert set(config["modules"]["tea"]["skills"]) == _TEA_ALL_SKILL_NAMES
    assert not (tea_fixture / "_bmad/config.yaml").exists()


def test_provision_tea_module_yaml_answers_override_test_artifacts_only(tea_fixture, monkeypatch):
    """Story 46.3: `[modules.tea]` carries every module.yaml variable's
    answer, with `test_artifacts` overridden to the UNRESOLVED
    `"{output_folder}/planning-artifacts"` template -- never a pre-resolved
    path -- and every other variable (`tea_use_playwright_utils`,
    `ci_platform`) left at its own declared default."""
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    provision_module("tea", cwd=tea_fixture)

    config = tomllib.loads((tea_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8"))
    tea = config["modules"]["tea"]
    assert tea["test_artifacts"] == "{output_folder}/planning-artifacts"
    assert tea["tea_use_playwright_utils"] is True
    assert tea["ci_platform"] == "auto"
    # `code` is a scalar, not a `{default: ...}` variable -- never rendered.
    assert "code" not in tea


def test_provision_installer_preserves_sibling_config_toml_content(tea_fixture, monkeypatch):
    """AD-9: the roster writer must not disturb any other content already in
    `_bmad/custom/config.toml` -- hand-written prose comments included --
    when appending a new `[modules.<name>]` section. Superseded (Story
    46.2) version of this test's own `config.yaml`-sibling-keys shape,
    which no longer applies now that `_record_module_manifest` never
    touches `_bmad/config.yaml`."""
    custom_dir = tea_fixture / "_bmad" / "custom"
    custom_dir.mkdir(parents=True)
    existing = (
        "# hand-authored header comment, must survive byte-for-byte.\n"
        "[core]\n"
        'communication_language = "English"\n'
        "\n"
        "# skf prose comment block.\n"
        "[modules.skf]\n"
        'sidecar_path = "{project-root}/_bmad/_memory/forger-sidecar"\n'
    )
    (custom_dir / "config.toml").write_text(existing, encoding="utf-8")
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    provision_module("tea", cwd=tea_fixture)

    updated = (custom_dir / "config.toml").read_text(encoding="utf-8")
    assert updated.startswith(existing), "pre-existing content must be untouched"
    parsed = tomllib.loads(updated)
    assert parsed["modules"]["skf"]["sidecar_path"] == ("{project-root}/_bmad/_memory/forger-sidecar")
    assert parsed["modules"]["tea"]["installer"] == "bmad-tea-install"


def test_provision_installer_idempotent_config_toml_rewrite_replaces_in_place(tea_fixture, monkeypatch):
    """Re-provisioning must replace the existing `[modules.tea]` section in
    place -- not duplicate it -- and leave the rest of the file byte-for-byte
    unchanged between the two runs."""
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    provision_module("tea", cwd=tea_fixture)
    config_path = tea_fixture / "_bmad/custom/config.toml"
    first = config_path.read_text(encoding="utf-8")

    provision_module("tea", cwd=tea_fixture)
    second = config_path.read_text(encoding="utf-8")

    assert second == first
    assert first.count("[modules.tea]") == 1


def test_provision_tea_flatten_idempotent_across_reprovision(tea_fixture, monkeypatch):
    """Story 46.3: a re-provision re-runs the (fake) installer, which has no
    notion of the flattened layout and so writes a FRESH `testarch`
    container right back to `dest/testarch` on every run. The flatten step
    must discard that re-written duplicate rather than leave it behind
    (which would fail the post-flatten "still has unexpected entries"
    check) -- reproduces a live bug caught by hand against the real
    `bmad-tea-install` binary and share tree before this test existed."""
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    provision_module("tea", cwd=tea_fixture)
    provision_module("tea", cwd=tea_fixture)
    third = provision_module("tea", cwd=tea_fixture)

    assert set(third["skills_installed"]) == _TEA_ALL_SKILL_NAMES
    for skill in _TEA_ALL_SKILL_NAMES:
        assert (tea_fixture / ".claude/skills" / skill).is_dir(), skill
    assert not (tea_fixture / ".claude/skills/testarch").exists()


def test_provision_tea_flatten_refreshes_stale_content_on_reprovision(tea_fixture, monkeypatch):
    """Review finding: an earlier draft's idempotency fix discarded the
    freshly-installed nested copy and kept the stale already-flattened
    target -- meaning a real TEA version bump would never actually reach
    the flattened skills after the first provision. Re-provisioning must
    adopt the fresh content instead."""
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    provision_module("tea", cwd=tea_fixture)
    flattened = tea_fixture / ".claude/skills/bmad-testarch-nfr/SKILL.md"
    assert flattened.read_text(encoding="utf-8") == "# bmad-testarch-nfr\n"

    # Simulate a real TEA package upgrade: the upstream share content for
    # one workflow changes.
    share_leaf = (
        tea_fixture
        / ".pixi/envs/pyforge-guild/share/bmad-method-test-architecture-enterprise"
        / "workflows/testarch/bmad-testarch-nfr/SKILL.md"
    )
    share_leaf.write_text("# bmad-testarch-nfr (v2, upgraded)\n", encoding="utf-8")

    provision_module("tea", cwd=tea_fixture)

    assert flattened.read_text(encoding="utf-8") == "# bmad-testarch-nfr (v2, upgraded)\n"


def test_provision_installer_rewrite_of_non_last_section_preserves_trailing_content(tea_fixture, monkeypatch):
    """Review finding: rewriting `[modules.tea]` when it is NOT the file's
    last section must not swallow the blank line or hand-written comment
    that separates it from the section after it -- both belong to the rest
    of the file, never to the section being replaced."""
    custom_dir = tea_fixture / "_bmad" / "custom"
    custom_dir.mkdir(parents=True)
    existing = (
        "[modules.tea]\n"
        'installer = "stale-value"\n'
        "\n"
        "# skf prose comment block, describes the NEXT section.\n"
        "[modules.skf]\n"
        'sidecar_path = "{project-root}/_bmad/_memory/forger-sidecar"\n'
    )
    (custom_dir / "config.toml").write_text(existing, encoding="utf-8")
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    provision_module("tea", cwd=tea_fixture)

    updated = (custom_dir / "config.toml").read_text(encoding="utf-8")
    assert "\n\n# skf prose comment block, describes the NEXT section.\n[modules.skf]\n" in updated
    parsed = tomllib.loads(updated)
    assert parsed["modules"]["tea"]["installer"] == "bmad-tea-install"
    assert parsed["modules"]["skf"]["sidecar_path"] == ("{project-root}/_bmad/_memory/forger-sidecar")


def test_provision_prefers_local_share_over_ambient_conda_prefix(tea_fixture, monkeypatch):
    """Fresh-clone fixture share must win over a lean ambient CONDA_PREFIX."""
    lean = tea_fixture / "lean-prefix"
    lean.mkdir()
    monkeypatch.setenv("CONDA_PREFIX", str(lean))
    seen: list[str] = []

    def _tracking_run(cmd, **kwargs):
        seen.append((kwargs.get("env") or {}).get("CONDA_PREFIX", ""))
        return _fake_installer_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", _tracking_run)

    result = provision_module("tea", cwd=tea_fixture)

    assert result["installer"] == "bmad-tea-install"
    assert seen
    assert Path(seen[0]) == tea_fixture / ".pixi/envs/pyforge-guild"


def test_provision_installer_exit_0_but_skills_missing_raises(tea_fixture, monkeypatch):
    """Story 46.3: a completely no-op installer never wrote `dest/testarch`
    at all, so the FLATTEN step (which now runs before the missing-skills
    check for a `flatten_nested_dirs` backend) is what raises first --
    naming what it expected vs. found, per this story's own I/O Matrix
    ("If flattening can't find the expected nested container, raise a
    clear RuntimeError")."""

    def _noop_installer(cmd, **kwargs):  # noqa: ARG001
        return subprocess.CompletedProcess(cmd, 0, stdout="Installed 0\n", stderr="")

    monkeypatch.setattr(subprocess, "run", _noop_installer)

    with pytest.raises(RuntimeError, match="expected .* to exist"):
        provision_module("tea", cwd=tea_fixture)

    assert not (tea_fixture / "_bmad/config.yaml").exists()
    assert not (tea_fixture / "_bmad/custom/config.toml").exists()


def test_provision_installer_missing_non_nested_skill_after_successful_flatten_raises(tea_fixture, monkeypatch):
    """Story 46.3: the predicted-vs-actual name check still catches a
    genuinely missing skill post-flatten -- here the `workflows` container
    installs and flattens cleanly, but `agents/bmad-tea` (a non-nested
    source, untouched by flattening) never got installed at all."""

    def _installer_skips_agents(cmd, **kwargs):
        dest = Path(cmd[1])
        dest.mkdir(parents=True, exist_ok=True)
        cwd = Path(kwargs.get("cwd") or ".")
        prefix = Path((kwargs.get("env") or {}).get("CONDA_PREFIX", cwd / ".pixi/envs/pyforge-guild"))
        share_root = prefix / "share" / "bmad-method-test-architecture-enterprise"
        shutil.copytree(share_root / "workflows" / "testarch", dest / "testarch")
        return subprocess.CompletedProcess(cmd, 0, stdout="Installed 1 skill(s)\n", stderr="")

    monkeypatch.setattr(subprocess, "run", _installer_skips_agents)

    with pytest.raises(RuntimeError, match="skills still missing"):
        provision_module("tea", cwd=tea_fixture)

    # The flatten step itself succeeded -- the nine workflow leaves landed
    # and `testarch` no longer exists -- it is only the unrelated
    # non-nested `bmad-tea` skill that is missing.
    assert not (tea_fixture / ".claude/skills/testarch").exists()
    for leaf in _TEA_WORKFLOW_LEAF_NAMES:
        assert (tea_fixture / ".claude/skills" / leaf).is_dir(), leaf
    assert not (tea_fixture / ".claude/skills/bmad-tea").exists()


def test_discovery_backends_skill_names_are_disjoint_in_fixture(tmp_path):
    """Always-on disjointness for discovery backends (no live pixi env).
    Story 46.3: TEA's `workflows` source is staged in its real NESTED shape
    -- `_installer_skill_names` predicts the flattened leaf names, never
    the `testarch` container name itself."""
    tea_pkg = "bmad-method-test-architecture-enterprise"
    util_pkg = "bmad-utility-skills"
    _stage_share_skills(tmp_path, package=tea_pkg, source_dir="agents", skill_names=("bmad-tea",))
    _stage_nested_share_skills(
        tmp_path,
        package=tea_pkg,
        source_dir="workflows",
        container="testarch",
        leaf_names=_TEA_WORKFLOW_LEAF_NAMES,
    )
    _stage_share_skills(
        tmp_path,
        package=util_pkg,
        source_dir="skills",
        skill_names=("bmad-os-gh-triage",),
    )
    share = tmp_path / ".pixi/envs/pyforge-guild/share"
    claimed: dict[str, str] = {}
    for name, backend in _SUPPORTED_MODULES.items():
        if not isinstance(backend, CondaInstallBackend):
            continue
        share_root = share / backend.share_package
        if not share_root.is_dir():
            continue
        for skill in _installer_skill_names(backend, share_root=share_root):
            assert skill not in claimed, f"skill {skill!r} claimed by both {claimed[skill]!r} and {name!r}"
            claimed[skill] = name
    assert set(claimed) >= {"bmad-tea", "bmad-testarch-nfr", "bmad-os-gh-triage"}
    assert "testarch" not in claimed


def test_provision_cis_via_installer_records_manifest(cis_fixture, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    result = provision_module("cis", cwd=cis_fixture)

    assert result["installer"] == "bmad-cis-install"
    assert len(result["skills_installed"]) == 10
    config = tomllib.loads((cis_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8"))
    assert config["modules"]["cis"]["installer"] == "bmad-cis-install"


@pytest.mark.parametrize(
    ("module_name", "package", "source_dir", "skills", "installer"),
    [
        (
            "utility-skills",
            "bmad-utility-skills",
            "skills",
            ("bmad-os-gh-triage", "bmad-os-review-pr"),
            "bmad-utility-skills-install",
        ),
        (
            "manticore",
            "bmad-manticore",
            "skills",
            ("mc-agent", "mc-setup"),
            "bmad-manticore-install",
        ),
    ],
)
def test_provision_utility_and_manticore_via_installer(
    tmp_path, monkeypatch, module_name, package, source_dir, skills, installer
):
    _stage_share_skills(tmp_path, package=package, source_dir=source_dir, skill_names=skills)
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    result = provision_module(module_name, cwd=tmp_path)

    assert result["installer"] == installer
    assert set(result["skills_installed"]) == set(skills)
    config = tomllib.loads((tmp_path / "_bmad/custom/config.toml").read_text(encoding="utf-8"))
    assert module_name in config["modules"]


def test_provision_installer_refuses_skill_name_collision(tea_fixture, monkeypatch):
    """Foreign skill already present + module not yet manifest-recorded →
    RuntimeError before any subprocess."""
    collision = tea_fixture / ".claude/skills/bmad-tea"
    collision.mkdir(parents=True)
    (collision / "SKILL.md").write_text("# foreign\n", encoding="utf-8")
    calls: list[object] = []

    def _tracking_run(cmd, **kwargs):
        calls.append(cmd)
        return _fake_installer_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", _tracking_run)

    with pytest.raises(RuntimeError, match="skill-name collision"):
        provision_module("tea", cwd=tea_fixture)

    assert calls == []


def test_provision_installer_refuses_malformed_destination_toml(tea_fixture, monkeypatch):
    """Post-AD-9 equivalent of the legacy YAML writer's "must be a mapping"
    refusal: `_record_module_manifest` must not text-edit a destination
    that isn't valid TOML today, even though its own line-based editor
    doesn't otherwise need a full parse to do its job."""
    custom_dir = tea_fixture / "_bmad" / "custom"
    custom_dir.mkdir(parents=True)
    (custom_dir / "config.toml").write_text("not [ valid toml", encoding="utf-8")
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    with pytest.raises(RuntimeError, match="is not valid TOML"):
        provision_module("tea", cwd=tea_fixture)


def test_provision_installer_idempotent_reprovision_allows_overwrite(tea_fixture, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)
    provision_module("tea", cwd=tea_fixture)
    # Second run: skills exist but module is manifest-recorded → allowed.
    second = provision_module("tea", cwd=tea_fixture)
    assert second["installer"] == "bmad-tea-install"


def test_provision_installer_missing_share_raises_before_subprocess(tmp_path, monkeypatch):
    # Pin the ambient prefix to an empty env: under a fat env (pyforge-guild
    # ships the tea share tree) the "missing share" this test asserts is not
    # missing, and the failure reads as a regression it is not.
    monkeypatch.setenv("CONDA_PREFIX", str(tmp_path / "lean-env"))
    calls: list[object] = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))  # noqa: ARG005

    with pytest.raises(FileNotFoundError, match="share package is missing"):
        provision_module("tea", cwd=tmp_path)

    assert calls == []


def test_provision_wds_is_skip_decided_with_upstream_citation(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    calls: list[object] = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))  # noqa: ARG005

    result = ProvisionDuty().run(_full_namespace(module="wds"))

    assert result.ok is False
    assert "skip" in result.summary.lower() or "deprecated" in result.summary.lower()
    assert "bmad-ux" in result.summary or "install-matrix" in result.summary
    assert calls == []
    assert "wds" not in _SUPPORTED_MODULES


def test_provision_module_api_raises_skip_citation_for_wds(tmp_path):
    with pytest.raises(FileNotFoundError, match="deprecated"):
        provision_module("wds", cwd=tmp_path)


def test_provision_tea_via_cli_round_trips(tea_fixture, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tea_fixture)
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    rc = main(["provision", "--module", "tea"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "tea" in out
    assert "bmad-tea-install" in out


def test_provision_tea_json_emits_installer_steps(tea_fixture, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tea_fixture)
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    result = ProvisionDuty().run(_full_namespace(module="tea", json=True))

    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["installer"] == "bmad-tea-install"
    assert "bmad-tea" in payload["skills_installed"]


def test_provision_installer_failure_names_nothing_written(tea_fixture, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tea_fixture)

    def _boom(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="CONDA_PREFIX is not set")

    monkeypatch.setattr(subprocess, "run", _boom)

    result = ProvisionDuty().run(_full_namespace(module="tea"))

    assert result.ok is False
    assert "CONDA_PREFIX is not set" in result.summary
    assert "nothing was written to _bmad/custom/config.toml" in result.summary
    assert not (tea_fixture / "_bmad/config.yaml").exists()
    assert not (tea_fixture / "_bmad/custom/config.toml").exists()


def test_manifest_location_label_per_backend_kind():
    """`_manifest_location_label` (review finding: its `CondaInstallBackend`
    branch was untested at the two `_run_module` call sites that build a
    failure/state-unknown message, since `_provision_conda_install` has no
    natural mid-chain failure point after `_record_module_manifest` runs --
    a direct unit test of the pure label function is the correct, minimal
    coverage rather than forcing an artificial mid-chain failure that
    cannot occur via the real `provision_module` call for these backends)."""
    for name, backend in _SUPPORTED_MODULES.items():
        label = _manifest_location_label(name)
        if isinstance(backend, CondaInstallBackend):
            assert label == "_bmad/custom/config.toml", (name, label)
        elif isinstance(backend, SetupSkillBackend):
            assert label == "_bmad/config.yaml", (name, label)


def test_provision_installer_state_read_failure_names_could_not_confirm(tea_fixture, monkeypatch):
    """The "could not confirm whether ... was touched" branch (`state_after
    is None`): a malformed `_bmad/custom/config.toml` at the moment of a
    mid-run subprocess failure must name the new TOML path, not the legacy
    YAML one (review finding -- this branch was previously only exercised,
    if at all, against `bmb`'s legacy-path label)."""
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tea_fixture)
    custom_dir = tea_fixture / "_bmad/custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    (custom_dir / "config.toml").write_text("not [ valid toml", encoding="utf-8")

    def _boom(cmd, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="CONDA_PREFIX is not set")

    monkeypatch.setattr(subprocess, "run", _boom)

    result = ProvisionDuty().run(_full_namespace(module="tea"))

    assert result.ok is False
    assert "could not confirm whether _bmad/custom/config.toml was touched" in result.summary


def test_provision_does_not_register_method_loop_skf_labs_dashboards_template():
    """Story 15.3 boundaries: never absorb core/loop/skf/labs/dashboards/
    template via `--module`."""
    forbidden = {
        "method",
        "bmad-method",
        "loop",
        "bmad-loop",
        "skf",
        "skill-forge",
        "labs",
        "labs-skills",
        "dashboard",
        "dashboards",
        "template",
        "module-template",
        "wds",
    }
    assert forbidden.isdisjoint(_SUPPORTED_MODULES)


def test_flatten_and_module_yaml_fields_are_tea_only():
    """Story 46.3 boundaries: `flatten_nested_dirs` and
    `module_yaml_relative_path` are opt-in -- only `tea` sets either field;
    `cis`/`utility-skills`/`manticore` are completely unaffected."""
    for name in ("cis", "utility-skills", "manticore"):
        backend = _SUPPORTED_MODULES[name]
        assert isinstance(backend, CondaInstallBackend)
        assert backend.flatten_nested_dirs == (), name
        assert backend.module_yaml_relative_path is None, name

    tea = _SUPPORTED_MODULES["tea"]
    assert isinstance(tea, CondaInstallBackend)
    assert tea.flatten_nested_dirs == ("workflows",)
    assert tea.module_yaml_relative_path == Path("module.yaml")


def test_provision_tea_missing_module_yaml_raises_named_error(tea_fixture, monkeypatch):
    """Review finding: the friendly `module.yaml is missing` guard had no
    test -- without it, this exact condition still fails (Python's own
    bare `open()` raises `FileNotFoundError`), but with an unhelpful,
    context-free message. Prove the named message, not just that
    *something* raises."""
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)
    share_root = tea_fixture / ".pixi/envs/pyforge-guild/share/bmad-method-test-architecture-enterprise"
    (share_root / "module.yaml").unlink()

    with pytest.raises(FileNotFoundError, match="module.yaml is missing"):
        provision_module("tea", cwd=tea_fixture)

    assert not (tea_fixture / "_bmad/custom/config.toml").exists()


def test_provision_tea_non_mapping_module_yaml_raises_named_error(tea_fixture, monkeypatch):
    """Review finding: the sibling `bmb` path has a dedicated test for a
    non-mapping module.yaml (`test_provision_module_malformed_module_yaml_is_a_clean_runtime_error`
    in test_provision_module.py); the new tea/CondaInstallBackend path had
    none. Without this guard, `_module_yaml_answers` would raise a bare
    `AttributeError` ('list' object has no attribute 'items') instead."""
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)
    share_root = tea_fixture / ".pixi/envs/pyforge-guild/share/bmad-method-test-architecture-enterprise"
    (share_root / "module.yaml").write_text("- not-a-mapping\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="did not parse to a mapping"):
        provision_module("tea", cwd=tea_fixture)


def test_render_module_toml_section_rejects_reserved_answer_key():
    """Review finding: a module.yaml variable literally named `skills` (or
    `installer`/`provisioned_by`) would silently emit a duplicate TOML key
    -- invalid on the very next `tomllib.loads` -- with no guard catching
    it at render time."""
    from pyforge.steward.provision import _render_module_toml_section

    with pytest.raises(RuntimeError, match="reserved manifest key"):
        _render_module_toml_section(
            "tea",
            installer="bmad-tea-install",
            skills=("bmad-tea",),
            answers={"skills": "oops"},
        )


def test_toml_value_unsupported_type_names_the_module_and_key():
    """Review finding: `_toml_value`'s own `TypeError` had no module/key
    context, unlike every other error path in this file, and no test
    exercised its failure mode at all."""
    from pyforge.steward.provision import _render_module_toml_section

    with pytest.raises(TypeError, match=r"module 'tea'.*risk_threshold.*unsupported"):
        _render_module_toml_section(
            "tea",
            installer="bmad-tea-install",
            skills=("bmad-tea",),
            answers={"risk_threshold": 1},
        )


def test_provision_cis_via_installer_never_gains_module_yaml_answer_keys(cis_fixture, monkeypatch):
    """Story 46.3 boundaries: cis's `[modules.cis]` section carries only the
    three AD-9 fields (`provisioned_by`/`installer`/`skills`) -- no
    module.yaml-answer keys leak in for a backend that never declared
    `module_yaml_relative_path`."""
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    provision_module("cis", cwd=cis_fixture)

    config = tomllib.loads((cis_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8"))
    assert set(config["modules"]["cis"]) == {"provisioned_by", "installer", "skills"}


def test_module_yaml_answers_overrides_only_test_artifacts():
    """Unit-level coverage for `_module_yaml_answers` (Story 46.3): reuses
    `_module_variable_defaults` verbatim, overriding only `test_artifacts`;
    a module.yaml with no `test_artifacts` key at all is untouched (no
    KeyError, no key invented)."""
    module_yaml = yaml.safe_load(_TEA_MODULE_YAML_TEXT)
    answers = _module_yaml_answers(module_yaml)
    assert answers == {
        "test_artifacts": "{output_folder}/planning-artifacts",
        "tea_use_playwright_utils": True,
        "ci_platform": "auto",
    }

    no_test_artifacts = {"foo": {"default": "bar"}}
    assert _module_yaml_answers(no_test_artifacts) == {"foo": "bar"}
