"""Story 11.1 — mason persona consults conda-forge-expert; grammar + MCP only."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

STATION = "mason"
PERSONA = "bmad-agent-mason"
CONTENT_SKILL = "conda-forge-expert"
CONTENT_SKILL_MD = ".claude/skills/conda-forge-expert/SKILL.md"
ALLOWED_KINDS = frozenset({"consult_content_skill", "grammar", "mcp"})
FREELANCE_KINDS = frozenset({"filesystem", "fs", "http", "adhoc_http"})
MCP_PATH = f"/stations/{STATION}/mcp"
GOLDEN = "mason-doctor-e2e.json"
SKF_REPLACEMENT = ".claude/skills/pyforge-mason"
# The mason-owned CFE-rebuild campaign (SPEC-conda-forge-expert-rebuild, Epic 12) adds one
# equivalence-validation test file per compiled slice under CFE's own tests/integration/
# directory by design (Story 6.3 landed test_slice1_equivalence.py; Story 12.7 landed
# test_slice2_equivalence.py; slices 3-5 will add their own). These prove the compiled
# replacement matches the live original -- they do not edit SKILL.md, scripts/, reference/,
# guides/, or config/, so they are not a "CFE surface replaced" violation of AD-15/FR-45 in
# the sense this test guards against. Excluded here, narrowly, rather than widening the
# `named`/`dirty` checks below to ignore all of tests/.
_CFE_REBUILD_EQUIVALENCE_TEST_RE = re.compile(
    r"^\.claude/skills/conda-forge-expert/tests/integration/test_slice\d+_equivalence\.py$"
)


def _exclude_cfe_rebuild_equivalence_tests(paths: list[str]) -> list[str]:
    return [p for p in paths if not _CFE_REBUILD_EQUIVALENCE_TEST_RE.match(p)]
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
            if event.get("skill") != CONTENT_SKILL:
                raise PersonaContractError("consult must name conda-forge-expert")
            path = str(event.get("path") or "").replace("\\", "/")
            if path != CONTENT_SKILL_MD:
                raise PersonaContractError("consult path must be conda-forge-expert SKILL.md")
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


def _git_diff_names(*paths: str) -> list[str]:
    root = _repo_root()
    named = subprocess.check_output(
        ["git", "diff", "--name-only", "origin/main", "--", *paths],
        cwd=root,
        text=True,
    )
    return [line for line in named.splitlines() if line.strip()]


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
    assert "consult_content_skill" in kinds
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


def test_consult_of_skf_pyforge_mason_is_not_cfe():
    events = [
        {
            "kind": "consult_content_skill",
            "skill": "pyforge-mason",
            "path": ".claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md",
        },
        {"kind": "grammar", "argv": ["pyforge", "mason", "doctor"]},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError:
        return
    raise AssertionError("SKF pyforge-mason consult was accepted as CFE")


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
    assert CONTENT_SKILL in skill
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
    assert CONTENT_SKILL_MD in customize
    assert "pyforge mason" in customize
    assert MCP_PATH in customize
    assert "bmad-build" not in customize
    assert "skf-create-skill" in customize


def test_conda_forge_expert_not_replaced_or_skf_nested():
    root = _repo_root()
    cfe = root / ".claude" / "skills" / CONTENT_SKILL
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    assert not (cfe / "active").exists()
    assert not (cfe / "provenance-map.json").exists()
    version_dirs = [
        path
        for path in cfe.iterdir()
        if path.is_dir() and re.fullmatch(r"\d+\.\d+\.\d+", path.name)
    ]
    assert not version_dirs, f"CFE became version-nested SKF: {version_dirs}"
    for path in cfe.rglob("*"):
        if path.name in {"metadata.json", "SKILL.md"} and path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            assert "generated_by: create-skill" not in text
            assert '"generated_by": "create-skill"' not in text
    named = _exclude_cfe_rebuild_equivalence_tests(
        _git_diff_names(".claude/skills/conda-forge-expert")
    )
    dirty = _exclude_cfe_rebuild_equivalence_tests(
        _git_dirty_under(".claude/skills/conda-forge-expert", SKF_REPLACEMENT)
    )
    assert not named, f"this story must not edit conda-forge-expert: {named}"
    assert not dirty, f"untracked CFE/SKF replacement files: {dirty}"
    assert not (root / SKF_REPLACEMENT).exists()
    assert not list(cfe.rglob("metadata.json"))


def test_claude_and_agents_unchanged():
    named = _git_diff_names("CLAUDE.md", "AGENTS.md")
    assert not named, f"Wave A must not edit CLAUDE.md/AGENTS.md: {named}"


def test_does_not_mint_01_portal_mcp_or_persona():
    root = _repo_root()
    skills = root / ".claude" / "skills"
    for name in WORK_CLASS_01_PERSONAS:
        assert not (skills / name).exists()
    named = _git_diff_names(
        "src/shared/packages/django-mason",
        ".claude/skills/pyforge-mason",
        "src/platform",
    )
    assert not named, f"11.1 must not mint 01 portal/MCP/persona or edit platform: {named}"


def test_story_does_not_add_pyforge_under_src_platform():
    root = _repo_root()
    changed = _git_diff_names("src/platform")
    offenders: list[str] = []
    for rel in changed:
        path = root / rel
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", maxsplit=1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".", maxsplit=1)[0]]
            if "pyforge" in names:
                offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
