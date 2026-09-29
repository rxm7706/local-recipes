"""Story 27.1: marshal persona acts only through grammar and MCP."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pyforge.testing_kit import changed_paths_since, pyforge_import_offenders

STATION = "marshal"
PERSONA = "bmad-agent-marshal"
CONTENT_SKILL = f"pyforge-{STATION}"
CONTENT_SKILL_MD = f".claude/skills/{CONTENT_SKILL}/active/{CONTENT_SKILL}/SKILL.md"
ALLOWED_KINDS = frozenset({"consult_content_skill", "grammar", "mcp"})
FREELANCE_KINDS = frozenset({"filesystem", "fs", "http", "adhoc_http"})
MCP_PATH = f"/stations/{STATION}/mcp"


class PersonaContractError(AssertionError):
    """Transcript or skill violates CAP-16."""


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
        kind = event.get("kind")
        if kind in FREELANCE_KINDS:
            raise PersonaContractError(f"freelance {kind}")
        if kind not in ALLOWED_KINDS:
            raise PersonaContractError(f"disallowed kind {kind!r}")
        if kind == "consult_content_skill":
            if event.get("skill") != CONTENT_SKILL:
                raise PersonaContractError("consult must name the CAP-15 content skill")
            path = str(event.get("path") or "").replace("\\", "/")
            if CONTENT_SKILL_MD not in path and not path.endswith(f"{CONTENT_SKILL}/SKILL.md"):
                raise PersonaContractError("consult path must be the CAP-15 SKILL.md")
        elif kind == "grammar":
            argv = event.get("argv") or []
            if len(argv) < 3 or argv[0] != "pyforge" or argv[1] != STATION:
                raise PersonaContractError("grammar must be pyforge <station> …")
            saw_surface = True
        elif kind == "mcp":
            if event.get("method") != "POST":
                raise PersonaContractError("mcp must be POST")
            if event.get("path") != MCP_PATH:
                raise PersonaContractError(f"mcp path must be {MCP_PATH}")
            saw_surface = True
    if not saw_surface:
        raise PersonaContractError("station task must use FR-13 grammar or FR-11 MCP")


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


def test_golden_transcript_is_grammar_and_mcp_only():
    root = _repo_root()
    path = _persona_dir(root) / "transcripts" / "marshal-status-e2e.json"
    events = json.loads(path.read_text(encoding="utf-8"))
    validate_transcript(events)
    kinds = {event["kind"] for event in events}
    assert "consult_content_skill" in kinds
    assert "grammar" in kinds
    assert "mcp" in kinds
    assert kinds <= ALLOWED_KINDS


def test_freelance_filesystem_in_transcript_fails():
    root = _repo_root()
    events = json.loads((_persona_dir(root) / "transcripts" / "marshal-status-e2e.json").read_text(encoding="utf-8"))
    events.append({"kind": "filesystem", "path": ".bmad-loops/journal.jsonl"})
    try:
        validate_transcript(events)
    except PersonaContractError as exc:
        assert "freelance" in str(exc)
        return
    raise AssertionError("filesystem freelance was permitted")


def test_adhoc_http_in_transcript_fails():
    root = _repo_root()
    events = json.loads((_persona_dir(root) / "transcripts" / "marshal-status-e2e.json").read_text(encoding="utf-8"))
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
        {"kind": "grammar", "argv": ["marshal", "status"]},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError:
        return
    raise AssertionError("bare marshal binary was accepted as FR-13 grammar")


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
    raise AssertionError("GET MCP was accepted as FR-11")


def test_mcp_other_station_is_not_marshal_face():
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
    raise AssertionError("scribe MCP was accepted as the marshal face")


def test_live_persona_skill_forbids_filesystem_and_adhoc_http():
    root = _repo_root()
    skill = (_persona_dir(root) / "SKILL.md").read_text(encoding="utf-8")
    assert_skill_forbids_freelance(skill)
    assert CONTENT_SKILL in skill
    assert "pyforge marshal" in skill
    assert MCP_PATH in skill
    assert "_bmad/scripts/resolve_customization.py" in skill


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
    assert "pyforge marshal" in customize
    assert MCP_PATH in customize
    assert "bmad-build" not in customize
    assert 'code = "WATCH"' in customize
    assert "pyforge marshal watch" in customize


def test_watch_menu_transcript_is_grammar_only():
    root = _repo_root()
    path = _persona_dir(root) / "transcripts" / "marshal-watch-e2e.json"
    events = json.loads(path.read_text(encoding="utf-8"))
    validate_transcript(events)
    grammar = [event for event in events if event["kind"] == "grammar"]
    assert grammar[0]["argv"][:3] == ["pyforge", "marshal", "watch"]


def test_consults_cap15_content_skill_on_disk():
    root = _repo_root()
    content = root / ".claude" / "skills" / CONTENT_SKILL / "active" / CONTENT_SKILL / "SKILL.md"
    assert content.is_file()
    body = content.read_text(encoding="utf-8")
    assert "marshal status" in body


def test_conda_forge_expert_not_replaced():
    root = _repo_root()
    cfe = root / ".claude" / "skills" / "conda-forge-expert"
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    assert not (cfe / "active").exists()


def test_story_does_not_add_pyforge_under_src_platform():
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    offenders = pyforge_import_offenders(changed, root)
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
