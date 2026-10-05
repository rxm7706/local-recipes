"""Story 11.1 — mason persona consults conda-forge-expert; grammar + MCP only."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from pyforge.testing_kit import (
    cfe_surface,
    changed_paths_since,
    commit_files,
    commits_since,
    pyforge_import_offenders,
    unsanctioned_commits,
)

STATION = "mason"
PERSONA = "bmad-agent-mason"
STATION_SKILL = "pyforge-mason"
STATION_SKILL_MD = ".claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md"
CONTENT_SKILL = "conda-forge-expert"
CONTENT_SKILL_MD = ".claude/skills/conda-forge-expert/SKILL.md"
CONSULT_SKILLS = frozenset({STATION_SKILL, CONTENT_SKILL})
ALLOWED_KINDS = frozenset({"consult_content_skill", "grammar", "mcp"})
FREELANCE_KINDS = frozenset({"filesystem", "fs", "http", "adhoc_http"})
MCP_PATH = f"/stations/{STATION}/mcp"
GOLDEN = "mason-doctor-e2e.json"
WORK_CLASS_01_PERSONAS = (
    "bmad-agent-chrome-probe",
    "bmad-agent-infra-probe",
    "bmad-agent-recipe-experiment",
)


class PersonaContractError(AssertionError):
    """Transcript or skill violates mason Path B / CAP-16."""


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _persona_dir(root: Path) -> Path:
    return root / ".claude" / "skills" / PERSONA


def _section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    return match.group(1) if match else ""


def validate_transcript(events: list[dict]) -> None:
    if not events:
        raise PersonaContractError("empty transcript")
    saw_surface = False
    for event in events:
        if not isinstance(event, dict):
            raise PersonaContractError("transcript event must be an object")
        kind = event.get("kind")
        if kind in FREELANCE_KINDS:
            raise PersonaContractError(f"freelance {kind}")
        if kind not in ALLOWED_KINDS:
            raise PersonaContractError(f"disallowed kind {kind!r}")
        if kind == "consult_content_skill":
            skill = event.get("skill")
            if skill not in CONSULT_SKILLS:
                raise PersonaContractError("consult must name pyforge-mason or conda-forge-expert")
            path = str(event.get("path") or "").replace("\\", "/")
            expected = STATION_SKILL_MD if skill == STATION_SKILL else CONTENT_SKILL_MD
            if path != expected:
                raise PersonaContractError(f"consult path must be {expected}")
        elif kind == "grammar":
            argv = event.get("argv") or []
            if not isinstance(argv, list):
                raise PersonaContractError("grammar argv must be a list")
            if len(argv) < 3 or argv[0] != "pyforge" or argv[1] != STATION:
                raise PersonaContractError("grammar must be pyforge mason …")
            saw_surface = True
        elif kind == "mcp":
            if event.get("method") != "POST":
                raise PersonaContractError("mcp must be POST")
            if event.get("path") != MCP_PATH:
                raise PersonaContractError(f"mcp path must be {MCP_PATH}")
            url = str(event.get("url") or "")
            if url and MCP_PATH not in url.replace("\\", "/"):
                raise PersonaContractError("mcp url must target the mason face")
            saw_surface = True
    if not saw_surface:
        raise PersonaContractError("station task must use pyforge mason grammar or mason MCP")


def assert_skill_forbids_freelance(text: str) -> None:
    allowed = _section(text, "Allowed actions (CAP-16)")
    forbidden = _section(text, "Forbidden actions")
    if not allowed.strip():
        raise PersonaContractError("persona skill missing Allowed actions (CAP-16)")
    if not forbidden.strip():
        raise PersonaContractError("persona skill missing Forbidden actions")
    if re.search(r"(?i)\b(read|write|delete|strreplace)\b tool", allowed):
        raise PersonaContractError("persona is allowed to use filesystem tools")
    if re.search(r"(?i)\b(curl|requests|httpx|webfetch|websearch|urllib)\b", allowed):
        raise PersonaContractError("persona is allowed to use ad-hoc HTTP")
    if re.search(r"(?i)direct filesystem", allowed) and "no direct" not in allowed.lower():
        raise PersonaContractError("persona is allowed to use filesystem")
    if not re.search(r"(?i)no direct filesystem", forbidden):
        raise PersonaContractError("persona skill does not forbid direct filesystem")
    if not re.search(r"(?i)no ad-hoc HTTP", forbidden):
        raise PersonaContractError("persona skill does not forbid ad-hoc HTTP")


def _git_dirty_under(*prefixes: str) -> list[str]:
    root = _repo_root()
    porcelain = subprocess.check_output(
        ["git", "status", "--porcelain", "-uall", "--", *prefixes],
        cwd=root,
        text=True,
    )
    dirty: list[str] = []
    for line in porcelain.splitlines():
        path = line[3:].strip()
        if path:
            dirty.append(path)
    return dirty


def test_golden_transcript_is_grammar_and_mcp_only():
    root = _repo_root()
    path = _persona_dir(root) / "transcripts" / GOLDEN
    events = json.loads(path.read_text(encoding="utf-8"))
    validate_transcript(events)
    kinds = {event["kind"] for event in events}
    consult_skills = {
        event["skill"] for event in events if event.get("kind") == "consult_content_skill"
    }
    assert consult_skills == CONSULT_SKILLS
    assert "grammar" in kinds
    assert "mcp" in kinds
    assert kinds <= ALLOWED_KINDS


def test_freelance_filesystem_in_transcript_fails():
    root = _repo_root()
    events = json.loads((_persona_dir(root) / "transcripts" / GOLDEN).read_text(encoding="utf-8"))
    events.append({"kind": "filesystem", "path": "recipes/example/recipe.yaml"})
    try:
        validate_transcript(events)
    except PersonaContractError as exc:
        assert "freelance" in str(exc)
        return
    raise AssertionError("filesystem freelance was permitted")


def test_adhoc_http_in_transcript_fails():
    root = _repo_root()
    events = json.loads((_persona_dir(root) / "transcripts" / GOLDEN).read_text(encoding="utf-8"))
    events.append({"kind": "http", "method": "GET", "url": "https://example.com"})
    try:
        validate_transcript(events)
    except PersonaContractError as exc:
        assert "freelance" in str(exc)
        return
    raise AssertionError("ad-hoc HTTP freelance was permitted")


def test_station_binary_without_pyforge_grammar_fails():
    events = [
        {
            "kind": "consult_content_skill",
            "skill": CONTENT_SKILL,
            "path": CONTENT_SKILL_MD,
        },
        {"kind": "grammar", "argv": ["mason", "doctor"]},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError:
        return
    raise AssertionError("bare mason binary was accepted as grammar")


def test_mcp_get_is_not_the_service_face():
    events = [
        {
            "kind": "consult_content_skill",
            "skill": CONTENT_SKILL,
            "path": CONTENT_SKILL_MD,
        },
        {"kind": "mcp", "method": "GET", "path": MCP_PATH},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError:
        return
    raise AssertionError("GET MCP was accepted as the mason face")


def test_third_content_skill_consult_fails():
    events = [
        {
            "kind": "consult_content_skill",
            "skill": STATION_SKILL,
            "path": STATION_SKILL_MD,
        },
        {
            "kind": "consult_content_skill",
            "skill": CONTENT_SKILL,
            "path": CONTENT_SKILL_MD,
        },
        {
            "kind": "consult_content_skill",
            "skill": "pyforge-steward",
            "path": ".claude/skills/pyforge-steward/active/pyforge-steward/SKILL.md",
        },
        {"kind": "grammar", "argv": ["pyforge", "mason", "doctor"]},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError as exc:
        assert "pyforge-steward" in str(exc) or "consult" in str(exc)
        return
    raise AssertionError("third skill consult was permitted")


def test_consult_path_must_be_exact_cfe_skill_md():
    events = [
        {
            "kind": "consult_content_skill",
            "skill": CONTENT_SKILL,
            "path": "tmp/evil/.claude/skills/conda-forge-expert/SKILL.md",
        },
        {"kind": "grammar", "argv": ["pyforge", "mason", "doctor"]},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError:
        return
    raise AssertionError("substring CFE path was accepted as the operating skill")


def test_mcp_other_station_is_not_mason_face():
    events = [
        {
            "kind": "consult_content_skill",
            "skill": CONTENT_SKILL,
            "path": CONTENT_SKILL_MD,
        },
        {"kind": "mcp", "method": "POST", "path": "/stations/scribe/mcp"},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError:
        return
    raise AssertionError("scribe MCP was accepted as the mason face")


def test_live_persona_skill_forbids_filesystem_and_adhoc_http():
    root = _repo_root()
    skill = (_persona_dir(root) / "SKILL.md").read_text(encoding="utf-8")
    assert_skill_forbids_freelance(skill)
    assert STATION_SKILL in skill
    assert CONTENT_SKILL in skill
    assert STATION_SKILL_MD.replace("\\", "/") in skill.replace("\\", "/")
    assert "pyforge mason" in skill
    assert MCP_PATH in skill
    assert "_bmad/scripts/resolve_customization.py" in skill
    assert "skf-create-skill" in skill


def test_permissive_skill_text_fails_contract():
    live = (_persona_dir(_repo_root()) / "SKILL.md").read_text(encoding="utf-8")
    allowed = "## Allowed actions (CAP-16)\n\n- You may use the Read tool and curl https://example.com\n"
    forbidden = "## Forbidden actions\n\nNothing.\n"
    permissive = re.sub(
        r"(?ms)^## Allowed actions \(CAP-16\).*?(?=^## Forbidden actions)",
        allowed,
        live,
    )
    permissive = re.sub(
        r"(?ms)^## Forbidden actions.*",
        forbidden,
        permissive,
    )
    try:
        assert_skill_forbids_freelance(permissive)
    except PersonaContractError:
        return
    raise AssertionError("permissive persona skill was accepted")


def test_persona_is_bmad_launcher_not_skf_compiled():
    root = _repo_root()
    persona = _persona_dir(root)
    assert (persona / "SKILL.md").is_file()
    assert (persona / "customize.toml").is_file()
    assert not (persona / "metadata.json").exists()
    assert not (persona / "provenance-map.json").exists()
    assert not (persona / "active").exists()
    customize = (persona / "customize.toml").read_text(encoding="utf-8")
    assert STATION_SKILL_MD in customize
    assert CONTENT_SKILL_MD in customize
    assert "pyforge mason" in customize
    assert MCP_PATH in customize
    assert "bmad-build" not in customize
    assert "skf-create-skill" in customize


def test_cfe_guard_reads_the_one_cfe_surface_owner():
    """Story 83.24: mason guard uses ``pyforge.testing_kit.cfe_surface``."""
    source = Path(__file__).read_text(encoding="utf-8")
    assert "cfe_surface.CFE_GIT_PATHSPECS" in source
    assert "cfe_surface.CFE_CHANGELOG_PATH" in source


def test_conda_forge_expert_not_replaced_or_skf_nested():
    root = _repo_root()
    cfe = root / ".claude" / "skills" / CONTENT_SKILL
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    assert not (cfe / "active").exists()
    assert not (cfe / "provenance-map.json").exists()
    version_dirs = [path for path in cfe.iterdir() if path.is_dir() and re.fullmatch(r"\d+\.\d+\.\d+", path.name)]
    assert not version_dirs, f"CFE became version-nested SKF: {version_dirs}"
    for path in cfe.rglob("*"):
        if path.name in {"metadata.json", "SKILL.md"} and path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            assert "generated_by: create-skill" not in text
            assert '"generated_by": "create-skill"' not in text
    unsanctioned = unsanctioned_commits(
        root,
        pathspec=cfe_surface.CFE_GIT_PATHSPECS,
        changelog_path=cfe_surface.CFE_CHANGELOG_PATH,
    )
    dirty = _git_dirty_under(".claude/skills/conda-forge-expert")
    assert not unsanctioned, (
        "this story must not edit conda-forge-expert outside a sanctioned `retro:` "
        f"commit that moves its CHANGELOG: {unsanctioned}"
    )
    assert not dirty, f"untracked CFE files: {dirty}"
    assert (root / ".claude" / "skills" / STATION_SKILL / "active").exists()
    assert not list(cfe.rglob("metadata.json"))


_MASON_SOURCE = "src/shared/packages/pyforge-mason/src"


def _mason_commits_touching(*paths: str) -> list[str]:
    """Files under ``paths`` edited by a commit on this branch that ALSO edits
    mason's own source tree -- i.e. by a mason story. The Wave A / 11.1
    invariants below are story-scoped ("a mason story must not mint these"),
    so they are checked per commit, not as a whole-branch diff: a fleet branch
    that also carries platform or context-file work is not a mason story
    editing the platform (2026-09-04, PR #1043)."""

    def _under(rel: str) -> bool:
        return any(rel == p or rel.startswith(f"{p}/") for p in paths)

    root = _repo_root()
    hits: list[str] = []
    for sha in commits_since(root, pathspec=_MASON_SOURCE, no_merges=True):
        files = [f for f in commit_files(root, sha) if _under(f)]
        hits.extend(f"{sha[:10]} {f}" for f in files)
    return hits


def test_claude_unchanged_by_mason_story_commits():
    named = _mason_commits_touching("CLAUDE.md")
    assert not named, f"Wave A must not edit CLAUDE.md: {named}"


def test_agents_skf_managed_section_well_formed():
    root = _repo_root()
    result = json.loads(
        subprocess.check_output(
            [
                sys.executable,
                str(root / ".claude" / "skills" / "shared" / "scripts" / "skf-rebuild-managed-sections.py"),
                str(root / "AGENTS.md"),
                "check",
            ],
            text=True,
        )
    )
    assert result["has_managed_section"]
    assert result["markers_valid"]


def test_does_not_mint_01_portal_mcp_or_persona():
    root = _repo_root()
    skills = root / ".claude" / "skills"
    for name in WORK_CLASS_01_PERSONAS:
        assert not (skills / name).exists()
    named = _mason_commits_touching(
        "src/shared/packages/django-mason",
        "src/platform",
    )
    assert not named, f"11.1 must not mint 01 portal/MCP/persona or edit platform: {named}"


def test_story_does_not_add_pyforge_under_src_platform():
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    offenders = pyforge_import_offenders(changed, root)
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
