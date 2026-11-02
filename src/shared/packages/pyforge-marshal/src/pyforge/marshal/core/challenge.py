"""The EGM challenger's pure core (spec-pyforge-marshal CAP-298..CAP-303, Epic 113).

A *challenge* is a fresh-context, read-only review of one chain artifact by the
Elephant-Goldfish Model's reviewer agents (``google/elephant-goldfish-model``,
a Claude Code plugin pinned by the ``[challenge].plugin_version`` policy key,
default ``0.1.0``, and checked against Claude Code's installed-plugins index and
the plugin cache's ``plugin.json``). The reviewers' ``omitClaudeMd`` needs Claude
Code 2.1.271 or later; below that floor the challenger refuses (Story 113.11).
Marshal never makes the model call and never loads a persona: it renders one task
prompt, a harness session spawns the plugin's registered agents, and Marshal reads
the session's JSON report back as data (AD-1).

Everything here is a pure function over values (AD-4): the stage vocabulary and
its default reviewer groups, the ``[challenge]`` policy block's shape check, the
goldfish context rule, the task prompt, the report's shape, and the resolve
bridge's accept/reject arithmetic. The CLI (``cli/challenge.py``) owns the I/O.
"""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from pyforge.core.errors import PyforgeError

from .model_cost import ADAPTER_TO_PROVIDER, provider_declaring_model

STAGES: tuple[str, ...] = ("mint", "decompose", "readiness", "drift", "rules")

# The plugin's registered reviewer agents, by persona name. The agent type a
# harness session spawns is ``egm:egm-<persona>``.
REVIEWER_PERSONAS: frozenset[str] = frozenset(
    {"zoom-out", "design", "comprehension", "implementation-readiness", "codebase-details"}
)
# EGM's document-structure and style personas judge an EGM design doc's shape;
# they would red every SPEC.md for not being one (CAP-299). Never dispatched.
FORBIDDEN_PERSONAS: frozenset[str] = frozenset({"structural", "style"})

DEFAULT_REVIEWERS: Mapping[str, tuple[str, ...]] = {
    "mint": ("zoom-out", "design", "comprehension"),
    "decompose": ("implementation-readiness", "codebase-details"),
    "readiness": ("implementation-readiness",),
    "drift": ("codebase-details", "zoom-out"),
    "rules": ("zoom-out", "design", "comprehension"),
}

EGM_PLUGIN_ID = "egm@egm"
EGM_MARKETPLACE = "egm"
EGM_MARKETPLACE_REPO = "google/elephant-goldfish-model"
EGM_PLUGIN_VERSION = "0.1.0"
DEFAULT_ARTIFACT_DIR = "implementation-artifacts/egm"
# Story 113.11 (CAP-298): Claude Code honours an agent's ``omitClaudeMd`` from 2.1.271 on.
CLAUDE_CODE_FLOOR: tuple[int, int, int] = (2, 1, 271)
_CLAUDE_CODE_VERSION = re.compile(r"\b(\d+)\.(\d+)\.(\d+)\b")

# The goldfish context rule (CAP-299): a reviewer never receives the house's
# instruction files, a memlog, a URL or session text.
_FORBIDDEN_CONTEXT_NAMES: frozenset[str] = frozenset({"AGENTS.md", "CLAUDE.md", "GEMINI.md", ".memlog.md", "MEMORY.md"})
# The team-memory index and its entries (``.claude/memory/``) are the house's memory too.
_FORBIDDEN_CONTEXT_SEGMENTS: tuple[tuple[str, str], ...] = ((".claude", "memory"),)

# The plugin's Claude adapter file for each persona (``.claude-plugin/agents/<file>.md``).
ADAPTER_FILES: Mapping[str, str] = {
    "zoom-out": "zoom_out.md",
    "design": "design_critic.md",
    "comprehension": "comprehension.md",
    "implementation-readiness": "implementation_readiness.md",
    "codebase-details": "codebase_details.md",
}
READ_ONLY_TOOLS: frozenset[str] = frozenset({"Read", "Grep", "Glob"})
_EGM_DOCUMENT_STANDARDS_SEGMENT = "document_standards"

SEVERITIES: tuple[str, ...] = ("high", "medium", "low")

CHALLENGE_BLOCK_KEYS: frozenset[str] = frozenset(
    {"enabled", "stages", "reviewers", "model", "standards", "artifact_dir", "plugin_version"}
)

# Story 113.9: the challenger runs on the packaged claude profile, so its model is an entry the
# claude adapter's catalog provider declares (``anthropic``).
CHALLENGER_PROVIDER = ADAPTER_TO_PROVIDER["claude"]
_MODEL_TOKEN_SPLIT = re.compile(r"[-._]")


def agent_type(persona: str) -> str:
    """The plugin-registered agent type a session spawns for ``persona``."""
    return f"egm:egm-{persona}"


@dataclass(frozen=True)
class ChallengeConfig:
    """The ``[challenge]`` policy block, composed (CAP-299). ``enabled=False``
    is the whole challenger off: every stage off, every hook a no-op."""

    enabled: bool = False
    stages: tuple[str, ...] = ()
    reviewers: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    model: str = ""
    standards: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    artifact_dir: str = DEFAULT_ARTIFACT_DIR
    plugin_version: str = EGM_PLUGIN_VERSION

    def stage_on(self, stage: str) -> bool:
        return self.enabled and stage in self.stages

    def reviewers_for(self, stage: str) -> tuple[str, ...]:
        return tuple(self.reviewers.get(stage) or DEFAULT_REVIEWERS[stage])


OFF = ChallengeConfig()


def _str_tuple(value: object) -> tuple[str, ...] | None:
    if isinstance(value, str) or not isinstance(value, Sequence):
        return None
    if not all(isinstance(item, str) and item for item in value):
        return None
    return tuple(value)


def _stage_map(value: object) -> dict[str, tuple[str, ...]] | None:
    if not isinstance(value, Mapping):
        return None
    result: dict[str, tuple[str, ...]] = {}
    for stage, entries in value.items():
        if stage not in STAGES:
            return None
        items = _str_tuple(entries)
        if items is None:
            return None
        result[stage] = items
    return result


def valid_challenge_block(value: object) -> dict[str, object] | None:
    """Shape check for the policy layer (``core/policy.py``'s validator
    convention: ``None`` excludes the whole layer). Semantic refusals that need
    the dispatching session's model are ``render_refusals``'s, not this one's."""
    if not isinstance(value, Mapping):
        return None
    if not set(value.keys()) <= CHALLENGE_BLOCK_KEYS:
        return None
    result: dict[str, object] = {}
    if "enabled" in value:
        if not isinstance(value["enabled"], bool):
            return None
        result["enabled"] = value["enabled"]
    if "stages" in value:
        stages = _str_tuple(value["stages"])
        if stages is None or not set(stages) <= set(STAGES):
            return None
        result["stages"] = list(stages)
    for key in ("reviewers", "standards"):
        if key in value:
            mapped = _stage_map(value[key])
            if mapped is None:
                return None
            result[key] = {stage: list(items) for stage, items in mapped.items()}
    for key in ("model", "artifact_dir", "plugin_version"):
        if key in value:
            if not isinstance(value[key], str) or not value[key].strip():
                return None
            result[key] = value[key]
    return result


def config_from_block(block: Mapping[str, object] | None) -> ChallengeConfig:
    """Compose a validated block into a ``ChallengeConfig``. An empty or absent
    block is ``OFF`` (absent means off, exactly as ``[context]`` behaves)."""
    if not block:
        return OFF
    return ChallengeConfig(
        enabled=bool(block.get("enabled", False)),
        stages=tuple(block.get("stages") or ()),  # type: ignore[arg-type]
        reviewers={k: tuple(v) for k, v in dict(block.get("reviewers") or {}).items()},  # type: ignore[call-overload]
        model=str(block.get("model") or ""),
        standards={k: tuple(v) for k, v in dict(block.get("standards") or {}).items()},  # type: ignore[call-overload]
        artifact_dir=str(block.get("artifact_dir") or DEFAULT_ARTIFACT_DIR),
        plugin_version=str(block.get("plugin_version") or EGM_PLUGIN_VERSION),
    )


def alias_of(model: str, aliases: Collection[str]) -> str | None:
    """The harness alias whose family ``model`` belongs to (Story 113.9), else ``None``.

    An alias such as ``sonnet`` names its family's current model, so a model id normalises to the
    alias that is one of its ``-``/``.``/``_``-separated tokens (``sonnet-5`` and
    ``claude-sonnet-4-5`` are ``sonnet``). An alias is its own family; ``default`` (the account's
    default) is a token of no id, so it matches only itself."""
    by_name = {alias.lower(): alias for alias in aliases if alias}
    lowered = model.lower()
    if lowered in by_name:
        return by_name[lowered]
    tokens = set(_MODEL_TOKEN_SPLIT.split(lowered))
    for name, alias in by_name.items():
        if name in tokens:
            return alias
    return None


def same_model(challenger: str, station_model: str, *, aliases: Collection[str]) -> bool:
    """CAP-299's same-model check, aliases normalised first (Story 113.9): equal ids are one model,
    and so are an alias and any id of its family -- whichever side carries the alias."""
    if challenger == station_model:
        return True
    challenger_alias = alias_of(challenger, aliases)
    station_alias = alias_of(station_model, aliases)
    return challenger_alias is not None and (station_model == challenger_alias or challenger == station_alias)


def render_refusals(
    config: ChallengeConfig,
    *,
    session_models: Sequence[str],
    model_cost_catalog: Mapping[str, object],
    aliases: Collection[str] = (),
) -> list[str]:
    """Refusals at policy render (CAP-299, Story 113.9): the challenger model must be an
    ``anthropic`` entry of ``model_cost_catalog`` (marshal's own, read for every ``--project``:
    the challenger runs on the packaged claude profile, which passes the id verbatim to
    ``claude --model``) and never one of the station's ``session_models``, an alias of either
    normalised first (``aliases``: the claude profile's ``[model_list]`` aliases). A
    structure/style persona or an EGM ``document_standards`` path is refused too."""
    reasons: list[str] = []
    if not config.enabled:
        return reasons
    if not config.model:
        reasons.append("[challenge].model is required when the block is enabled")
    else:
        provider = provider_declaring_model(model_cost_catalog, config.model)
        if provider is None:
            reasons.append(f"[challenge].model {config.model!r} is not a model_cost_catalog entry")
        elif provider != CHALLENGER_PROVIDER:
            reasons.append(
                f"[challenge].model {config.model!r} is catalogued under {provider!r}; the challenger runs on "
                f"the claude profile and takes only an {CHALLENGER_PROVIDER!r} entry"
            )
        clashes = sorted({m for m in session_models if m and same_model(config.model, m, aliases=aliases)})
        if clashes:
            reasons.append(
                f"[challenge].model {config.model!r} is the dispatching session's own model "
                f"({', '.join(clashes)}); the challenger must be a different model"
            )
    for stage, personas in config.reviewers.items():
        bad = sorted(set(personas) & FORBIDDEN_PERSONAS)
        if bad:
            reasons.append(
                f"[challenge].reviewers.{stage} names {bad}: EGM's structure and style personas are never dispatched"
            )
        unknown = sorted(set(personas) - REVIEWER_PERSONAS - FORBIDDEN_PERSONAS)
        if unknown:
            reasons.append(f"[challenge].reviewers.{stage} names unknown personas {unknown}")
    for stage, paths in config.standards.items():
        for path in paths:
            if _EGM_DOCUMENT_STANDARDS_SEGMENT in PurePosixPath(path).parts:
                reasons.append(
                    f"[challenge].standards.{stage} names EGM's own {path!r}; judge against the repo's standards"
                )
    return reasons


@dataclass(frozen=True)
class ChallengeContext:
    """Everything a reviewer receives (CAP-299), as absolute paths."""

    target: str
    glossary: str
    dream: str
    standards: tuple[str, ...]

    def context_paths(self) -> tuple[str, ...]:
        """The context a reviewer reads; a station with no glossary yet gets none (empty)."""
        return tuple(p for p in (self.glossary, self.dream, *self.standards) if p)


def context_violations(context: ChallengeContext) -> list[str]:
    """The goldfish context rule. The *target* may be a rules file such as
    ``AGENTS.md`` (the ``rules`` stage reads it cold); the *context* never is."""
    reasons: list[str] = []
    for path in (context.target, *context.context_paths()):
        if "://" in path:
            reasons.append(f"{path!r} is a URL; reviewers cannot open URLs")
        elif not PurePosixPath(path).is_absolute():
            reasons.append(f"{path!r} is not absolute")
    for path in context.context_paths():
        parts = PurePosixPath(path).parts
        in_memory = any(
            parts[i : i + len(seg)] == seg for seg in _FORBIDDEN_CONTEXT_SEGMENTS for i in range(len(parts))
        )
        if PurePosixPath(path).name in _FORBIDDEN_CONTEXT_NAMES or in_memory:
            reasons.append(f"{path!r} may not be goldfish context (instruction files, memory and memlogs stay out)")
    return reasons


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def adapter_isolation_violations(persona: str, text: str) -> list[str]:
    """CAP-299: a spawned reviewer must be the plugin adapter that omits the
    instruction files and holds read-only tools. ``text`` is the adapter file."""
    fields = _frontmatter(text)
    reasons: list[str] = []
    if fields.get("name") != f"egm-{persona}":
        reasons.append(f"adapter for {persona!r} names {fields.get('name')!r}, not 'egm-{persona}'")
    if fields.get("omitClaudeMd", "").lower() != "true":
        reasons.append(f"adapter egm-{persona} does not declare omitClaudeMd: true")
    tools = {t.strip() for t in fields.get("tools", "").strip("[]").split(",") if t.strip()}
    if not tools or not tools <= READ_ONLY_TOOLS:
        reasons.append(f"adapter egm-{persona} tools {sorted(tools)} are not read-only {sorted(READ_ONLY_TOOLS)}")
    return reasons


def installed_version_refusal(installed: Mapping[str, object], plugin_id: str, pinned: str) -> str | None:
    """S4: the version Claude Code actually has active (``installed_plugins.json``)
    must be the pinned one; a stale cache folder alone proves nothing."""
    plugins = installed.get("plugins") if isinstance(installed, Mapping) else None
    entries = plugins.get(plugin_id) if isinstance(plugins, Mapping) else None
    if not isinstance(entries, list) or not entries:
        return f"{plugin_id} is not in Claude Code's installed plugins"
    versions = sorted({str(e.get("version")) for e in entries if isinstance(e, Mapping)})
    if versions != [pinned]:
        return f"{plugin_id} is installed at {versions}, not the pinned {pinned!r}"
    return None


def claude_code_version_refusal(output: str | None) -> str | None:
    """Story 113.11 (CAP-298): ``None`` when ``claude --version``'s ``output`` names a version
    at or above ``CLAUDE_CODE_FLOOR``; otherwise the reason. No output, or output with no
    ``X.Y.Z`` in it, refuses too: a version that cannot be read cannot prove the floor."""
    floor = ".".join(str(part) for part in CLAUDE_CODE_FLOOR)
    match = _CLAUDE_CODE_VERSION.search(output or "")
    if match is None:
        shown = (output or "").strip()[:80]
        return f"cannot read Claude Code's version from `claude --version` ({shown!r}); the challenger needs >= {floor}"
    found = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    if found < CLAUDE_CODE_FLOOR:
        return f"Claude Code {match.group(0)} is below {floor}, the floor for the reviewers' omitClaudeMd"
    return None


_REPORT_SCHEMA_HINT = (
    '{"stage": "<stage>", "target": "<absolute path>", "reviewers": ["<agent type>", ...], '
    '"findings": [{"id": "F1", "reviewer": "<agent type>", "severity": "high|medium|low", '
    '"claim": "<one sentence>", "evidence": "<path or quote>"}]}'
)


def render_prompt(*, stage: str, personas: Sequence[str], context: ChallengeContext, report_path: str) -> str:
    """The one task prompt a harness session receives. It names the reviewer
    agents, hands each the target and its context paths and nothing else, and asks for
    one JSON report at ``report_path``."""
    agents = ", ".join(f"`{agent_type(p)}`" for p in personas)
    standards = "\n".join(f"  - {path}" for path in context.standards)
    glossary = f"  - glossary: {context.glossary}\n" if context.glossary else ""
    return (
        f"EGM challenge, stage `{stage}`. You are the orchestrator; you do not review.\n\n"
        f"Spawn one fresh agent per reviewer, in parallel, with the Agent tool: {agents}. "
        "Do not use the Skill tool. Do not fork this conversation or resume a reviewer.\n\n"
        "Give every reviewer exactly these absolute paths and nothing else - no instruction "
        "files, no memory, no memlog, no URL, none of this prompt's other text:\n"
        f"  - target: {context.target}\n"
        f"{glossary}"
        f"  - Dream (read the dated entry the target cites): {context.dream}\n"
        f"  - standard(s):\n{standards}\n\n"
        "Ask each reviewer for what does not make sense, what is assumed but never written, and "
        "what is promised but never tested in the target, judged against the standard(s).\n\n"
        f"When every reviewer has answered, write ONE JSON file to {report_path} with this shape "
        f"and nothing else in it:\n{_REPORT_SCHEMA_HINT}\n"
        "Number findings F1, F2, ... across all reviewers; drop exact duplicates. Write no other "
        "file and edit nothing in the repository."
    )


@dataclass(frozen=True)
class ReportFinding:
    id: str
    reviewer: str
    severity: str
    claim: str
    evidence: str
    resolution: str = ""
    reason: str = ""


@dataclass(frozen=True)
class ChallengeReport:
    stage: str
    target: str
    reviewers: tuple[str, ...]
    findings: tuple[ReportFinding, ...]
    project: str = ""
    spec_workspace: str = ""
    # Story 113.13: the Spec folder that governs a rules target outside its run's station, when one does.
    owner_override: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "stage": self.stage,
                "target": self.target,
                "project": self.project,
                "spec_workspace": self.spec_workspace,
                **({"owner_override": self.owner_override} if self.owner_override else {}),
                "reviewers": list(self.reviewers),
                "findings": [
                    {
                        "id": f.id,
                        "reviewer": f.reviewer,
                        "severity": f.severity,
                        "claim": f.claim,
                        "evidence": f.evidence,
                        **({"resolution": f.resolution} if f.resolution else {}),
                        **({"reason": f.reason} if f.reason else {}),
                    }
                    for f in self.findings
                ],
            },
            indent=2,
            sort_keys=False,
        )


class ReportError(PyforgeError, ValueError):
    """The session's report is missing a field or malformed."""


def parse_report(text: str) -> ChallengeReport:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReportError(f"report is not JSON: {exc}") from exc
    if not isinstance(data, Mapping):
        raise ReportError("report is not a JSON object")
    stage = data.get("stage")
    if stage not in STAGES:
        raise ReportError(f"report stage {stage!r} is not one of {STAGES}")
    raw_findings = data.get("findings")
    if not isinstance(raw_findings, list):
        raise ReportError("report has no findings list")
    findings: list[ReportFinding] = []
    seen: set[str] = set()
    for item in raw_findings:
        if not isinstance(item, Mapping):
            raise ReportError("a finding is not an object")
        fid = str(item.get("id") or "").strip()
        if not fid or fid in seen:
            raise ReportError(f"finding id {fid!r} is empty or repeated")
        seen.add(fid)
        severity = str(item.get("severity") or "").lower()
        if severity not in SEVERITIES:
            raise ReportError(f"finding {fid} severity {severity!r} is not one of {SEVERITIES}")
        findings.append(
            ReportFinding(
                id=fid,
                reviewer=str(item.get("reviewer") or ""),
                severity=severity,
                claim=str(item.get("claim") or ""),
                evidence=str(item.get("evidence") or ""),
                resolution=str(item.get("resolution") or ""),
                reason=str(item.get("reason") or ""),
            )
        )
    reviewers = data.get("reviewers") or []
    return ChallengeReport(
        stage=str(stage),
        target=str(data.get("target") or ""),
        reviewers=tuple(str(r) for r in reviewers) if isinstance(reviewers, list) else (),
        findings=tuple(findings),
        project=str(data.get("project") or ""),
        spec_workspace=str(data.get("spec_workspace") or ""),
        owner_override=str(data.get("owner_override") or ""),
    )


def unevaluable_reason(report: ChallengeReport, *, stage: str, personas: Sequence[str]) -> str | None:
    """Why a parsed report cannot be read as the requested review (CAP-298), else ``None``.

    The orchestrator writes the report's ``reviewers`` list itself, so a report that omits a
    dispatched reviewer, lists none, or names another stage did not fully run: unevaluable,
    never clean -- whatever its finding count."""
    if report.stage != stage:
        return f"report stage {report.stage!r} is not the requested {stage!r}"
    listed = {reviewer.strip() for reviewer in report.reviewers}
    if not listed - {""}:
        return "report lists no reviewers"
    missing = [agent_type(p) for p in personas if agent_type(p) not in listed]
    if missing:
        return f"report omits dispatched reviewer(s) {', '.join(missing)}"
    return None


# The finding code a red readiness review carries (CAP-300; ``cli/dispatch.py``'s launch hook, WARN).
READINESS_RED_CODE = "MRS-DISP-067"


def _count(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def readiness_view(payload: Mapping[str, object]) -> dict[str, object]:
    """The launch intent's ``readiness_challenge`` payload as ``marshal status`` and ``marshal
    watch`` show it (CAP-300): the report path, the counts, and ``red`` -- the review reported a
    finding or could not run, the same rule that raises ``MRS-DISP-067`` at launch -- with the
    code when red. Idempotent: a view reads back as itself."""
    error = str(payload.get("error") or "")
    findings = _count(payload.get("findings"))
    view: dict[str, object] = {
        "report": str(payload.get("report") or ""),
        "findings": findings,
        "high": _count(payload.get("high")),
        "error": error,
        "red": bool(error) or findings > 0,
    }
    if view["red"]:
        view["code"] = READINESS_RED_CODE
    return view


def readiness_text(view: Mapping[str, object]) -> str:
    """One line for a text renderer: ``clean`` or ``red MRS-DISP-067``, the detail, the report."""
    report = str(view.get("report") or "") or "(none)"
    if not view.get("red"):
        return f"clean, report {report}"
    detail = " ".join(str(view.get("error") or "").split()) or (
        f"{view.get('findings')} finding(s), {view.get('high')} high"
    )
    return f"red {view.get('code') or READINESS_RED_CODE}: {detail}; report {report}"


def with_provenance(
    report: ChallengeReport, *, project: str, spec_workspace: str, owner_override: str = ""
) -> ChallengeReport:
    """Stamp the run's project and the owning Spec folder; ``owner_override`` records a rules
    target's governor when it is not the project's own Spec (Story 113.13). ``resolve`` checks
    these against ``--project`` and never takes its write target from them (CAP-303)."""
    return ChallengeReport(
        stage=report.stage,
        target=report.target,
        reviewers=report.reviewers,
        findings=report.findings,
        project=project,
        spec_workspace=spec_workspace,
        owner_override=owner_override,
    )


@dataclass(frozen=True)
class Resolution:
    report: ChallengeReport
    memlog_lines: tuple[str, ...]


def resolve(
    report: ChallengeReport,
    *,
    accept: Mapping[str, str],
    reject: Mapping[str, str],
    report_path: str,
) -> Resolution:
    """The resolve bridge's arithmetic (CAP-303): one memlog line per accepted
    finding; rejected ids and reasons written back into the report. An id the
    report does not carry, or one both accepted and rejected, is refused."""
    known = {f.id for f in report.findings}
    unknown = sorted((set(accept) | set(reject)) - known)
    if unknown:
        raise ReportError(f"finding id(s) not in the report: {', '.join(unknown)}")
    both = sorted(set(accept) & set(reject))
    if both:
        raise ReportError(f"finding id(s) both accepted and rejected: {', '.join(both)}")
    done = sorted(f.id for f in report.findings if f.resolution and (f.id in accept or f.id in reject))
    if done:
        raise ReportError(f"finding id(s) already resolved: {', '.join(done)}")
    findings: list[ReportFinding] = []
    lines: list[str] = []
    for f in report.findings:
        if f.id in accept:
            note = accept[f.id].strip()
            lines.append(
                f"EGM challenge finding {f.id} accepted ({report.stage} stage, {f.severity}, {f.reviewer}): "
                f"{f.claim}{' Operator: ' + note if note else ''} Evidence: {f.evidence}. Report: {report_path}."
            )
            findings.append(_resolved(f, "accepted", note))
        elif f.id in reject:
            findings.append(_resolved(f, "rejected", reject[f.id].strip()))
        else:
            findings.append(f)
    resolved = ChallengeReport(
        stage=report.stage,
        target=report.target,
        reviewers=report.reviewers,
        findings=tuple(findings),
        project=report.project,
        spec_workspace=report.spec_workspace,
        owner_override=report.owner_override,
    )
    return Resolution(report=resolved, memlog_lines=tuple(lines))


def _resolved(f: ReportFinding, resolution: str, reason: str) -> ReportFinding:
    return ReportFinding(
        id=f.id,
        reviewer=f.reviewer,
        severity=f.severity,
        claim=f.claim,
        evidence=f.evidence,
        resolution=resolution,
        reason=reason,
    )


def memlog_command(*, script: str, workspace: str, text: str) -> str:
    """The exact command an operator pastes, from the repo root, to append ``text`` as a memlog
    event on ``workspace`` (Story 113.13, CAP-303): marshal writes only its own Spec, so an accepted
    finding any other Spec owns gets this line instead. Each value is shell-quoted as one argument."""
    return f"uv run {script} append --workspace {shlex.quote(workspace)} --type event --text {shlex.quote(text)}"


def parse_id_notes(entries: Sequence[str]) -> dict[str, str]:
    """``F3`` or ``F3:the operator's reason`` -> ``{"F3": "the operator's reason"}``."""
    result: dict[str, str] = {}
    for entry in entries:
        fid, _sep, note = entry.partition(":")
        fid = fid.strip()
        if not fid:
            raise ReportError(f"empty finding id in {entry!r}")
        result[fid] = note.strip()
    return result


def fleet_summary(station_reports: Mapping[str, Sequence[ChallengeReport]]) -> str:
    """The audit's fleet summary (CAP-302): counts per station and stage, then
    every high-severity finding, as Markdown."""
    lines = ["# EGM audit — fleet summary", "", "| Station | Stage | Findings | High |", "|---|---|---:|---:|"]
    highs: list[str] = []
    for station in sorted(station_reports):
        for report in station_reports[station]:
            high = [f for f in report.findings if f.severity == "high"]
            lines.append(f"| {station} | {report.stage} | {len(report.findings)} | {len(high)} |")
            highs.extend(f"- **{station} / {report.stage} / {f.id}** — {f.claim} ({f.evidence})" for f in high)
    lines += ["", "## High-severity findings", "", *(highs or ["_None._"])]
    return "\n".join(lines) + "\n"
