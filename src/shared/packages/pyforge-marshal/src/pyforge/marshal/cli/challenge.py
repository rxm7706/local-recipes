"""``marshal factory challenge`` -- the EGM challenger (Epic 113, CAP-298..CAP-303).

One verb, five stages, three run modes:

* **ad hoc** -- ``marshal factory challenge --project <slug> --stage <s> --target <path>``;
* **integrated** -- ``marshal factory dispatch`` runs the ``readiness`` stage on a
  story spec before its harness launches (``readiness_for_dispatch``), and a
  ``bmad-retrospective`` on a marshal epic runs ``--stage drift --epic <n>``;
* **audit** -- ``--audit`` sweeps every station's Dream, Spec and ``epics.md`` and
  the repo's rules once.

Every report lands under Tier 3 (``implementation-artifacts/egm/``), every run is
journaled, and the exit code carries only the verb's own refusals -- never a
finding (CAP-298). ``resolve`` turns accepted findings into memlog lines on the
owning Spec and nothing else (CAP-303). Six kill switches, all default off; the
``[challenge]`` policy block is the one configuration, and absent means off.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from pyforge.core.errors import PyforgeError
from pyforge.core.flags import FlagConfigError, read_boolean, require
from pyforge.core.process import PosixProcess, ProcessError
from pyforge.core.roster import STATIONS, long_form

from ..core import challenge as core
from ..core import policy
from ..core.journal import JournalEntryId, Phase, build_entry, mint_run_id, prepare_for_write
from ..core.model import Verdict
from ..core.verdict import EXIT_OK, EXIT_USAGE, exit_code_for
from .config import PolicyIOError, _read_project_policy, conventional_project_policy_path, read_repo_policy_defaults
from .config import repo_root as _default_repo_root

EGM_CHALLENGE_FLAG_KEY = "pyforge.marshal.egm_challenge"  # CAP-298, Story 113.1
EGM_POLICY_BLOCK_FLAG_KEY = "pyforge.marshal.egm_policy_block"  # CAP-299, Story 113.2
EGM_DISPATCH_READINESS_FLAG_KEY = "pyforge.marshal.egm_dispatch_readiness"  # CAP-300, Story 113.3
EGM_RETRO_DRIFT_FLAG_KEY = "pyforge.marshal.egm_retro_drift"  # CAP-301, Story 113.4
EGM_AUDIT_FLAG_KEY = "pyforge.marshal.egm_audit"  # CAP-302, Story 113.5
EGM_RESOLVE_BRIDGE_FLAG_KEY = "pyforge.marshal.egm_resolve_bridge"  # CAP-303, Story 113.6

PLUGINS_ROOT_ENV = "MARSHAL_EGM_PLUGINS_ROOT"
SETTINGS_RELPATH = ".claude/settings.json"
CHAIN_STANDARD_RELPATH = "docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md"
CHAIN_STANDARD_SPEC_RELPATH = "docs/governance/spec-one-chain-per-station/SPEC.md"
CHAIN_STANDARD_DREAM_RELPATH = "docs/dreams/one-chain-per-station.md"
STORY_SPEC_TEMPLATE_RELPATH = ".claude/skills/bmad-build-auto/spec-template.md"
MEMLOG_SCRIPT_RELPATH = "_bmad/scripts/memlog.py"
REPORT_FILENAME = "report.json"
JOURNAL_FILENAME = "journal.jsonl"
SESSION_LOG_FILENAME = "session.log"
KIND_CHALLENGE_RUN = "challenge-run"
KIND_DISPATCH_READINESS = "dispatch-challenge-readiness"
KIND_CHALLENGE_REFUSED = "challenge-refused"
KIND_AUDIT_SKIP = "challenge-audit-skip"

_HELP = "Fresh-context EGM review of one chain artifact (Epic 113)."


class ChallengeRunner(Protocol):
    def run(self, *, prompt: str, model: str | None, cwd: Path, log_path: Path) -> int: ...


class ChallengeRefused(PyforgeError, Exception):
    """A refusal the verb reports with the usage code; never a finding."""


@dataclass(frozen=True)
class RunOutcome:
    run_id: str
    run_dir: Path
    report_path: Path
    report: core.ChallengeReport | None
    error: str = ""


# --- argparse ---------------------------------------------------------------


def add_factory_challenge_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    # Static help: building the parser reads no flag (a read here would WARN on every `marshal` call
    # whose tree lacks the key). The switch is enforced in the handler (`require`), which refuses
    # with the usage code while the verb stays listed (spec-feature-flag-governance:CAP-7 Q3).
    help_text = f"{_HELP} Off unless {EGM_CHALLENGE_FLAG_KEY} is on."
    parser = factory_subparsers.add_parser("challenge", help=help_text, description=help_text)
    parser.add_argument("--project", help="The BMAD project slug whose [challenge] block configures the run.")
    parser.add_argument("--stage", choices=core.STAGES, help="Which review the goldfish run.")
    parser.add_argument("--target", help="The artifact to review (repo-relative or absolute).")
    parser.add_argument("--epic", help="With --stage drift: the epic number whose code is read against its Spec.")
    parser.add_argument(
        "--audit", action="store_true", help="Sweep every station's Dream, Spec, epics.md and the repo rules once."
    )
    parser.add_argument(
        "--force", action="store_true", help="With --audit: re-run stations whose report already exists."
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.set_defaults(handler=run_challenge, challenge_command=None)
    subs = parser.add_subparsers(dest="challenge_command", required=False)
    resolve_p = subs.add_parser("resolve", help="Accept or reject a report's findings (memlog lines only).")
    resolve_p.add_argument("--report", required=True, help="Path to a challenge report.json.")
    resolve_p.add_argument("--accept", action="append", default=[], metavar="ID[:NOTE]")
    resolve_p.add_argument("--reject", action="append", default=[], metavar="ID[:REASON]")
    resolve_p.set_defaults(handler=run_challenge)


# --- flags, policy, plugin ---------------------------------------------------


def flag_on(key: str) -> bool:
    """A default-off EGM switch. A broken tree reads as off: the challenger is
    never the reason a dispatch or a retro stops."""
    try:
        return read_boolean(key, default=False)
    except FlagConfigError:
        return False


def compose_effective(slug: str) -> policy.EffectivePolicy:
    repo_defaults, _finding = read_repo_policy_defaults()
    project_data: dict[str, object] = {}
    candidate = conventional_project_policy_path(slug)
    if candidate.is_file():
        try:
            project_data = dict(_read_project_policy(candidate))
        except PolicyIOError:
            project_data = {}
    effective, _findings = policy.compose(
        project_slug=slug, repo_defaults=repo_defaults, project=project_data, flags={}
    )
    return effective


def challenge_config(effective: policy.EffectivePolicy) -> core.ChallengeConfig:
    """The composed block, or ``OFF`` while the policy-block switch is off."""
    if not flag_on(EGM_POLICY_BLOCK_FLAG_KEY):
        return core.OFF
    value = effective.challenge.value
    return core.config_from_block(value if isinstance(value, Mapping) else None)


def session_models(effective: policy.EffectivePolicy) -> list[str]:
    """Every model the station's sessions author with (``model_tier_map``)."""
    models: list[str] = []
    tier_map = effective.model_tier_map.value
    if isinstance(tier_map, Mapping):
        for stages in tier_map.values():
            if isinstance(stages, Mapping):
                for entry in stages.values():
                    if isinstance(entry, Mapping) and isinstance(entry.get("model"), str):
                        models.append(entry["model"])
                    elif isinstance(entry, str):
                        models.append(entry)
    return models


def plugins_root(env: Mapping[str, str] | None = None) -> Path:
    raw = (env if env is not None else os.environ).get(PLUGINS_ROOT_ENV)
    return Path(raw) if raw else Path.home() / ".claude" / "plugins"


def plugin_refusal(root: Path, plugins: Path, version: str, personas: tuple[str, ...] = ()) -> str | None:
    """``None`` when ``egm@egm`` is enabled in the tracked settings, Claude Code's
    installed-plugins index holds exactly the pinned version, the cache manifest
    agrees, and every persona's adapter omits the instruction files and holds
    read-only tools; otherwise the reason (CAP-298, CAP-299)."""
    settings_path = root / SETTINGS_RELPATH
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"cannot read {SETTINGS_RELPATH}: {exc}"
    if (settings.get("enabledPlugins") or {}).get(core.EGM_PLUGIN_ID) is not True:
        return f"{core.EGM_PLUGIN_ID} is not enabled in {SETTINGS_RELPATH}"
    try:
        installed = json.loads((plugins / "installed_plugins.json").read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        installed = {}
    refusal = core.installed_version_refusal(installed, core.EGM_PLUGIN_ID, version)
    if refusal:
        return f"{refusal}; run: claude plugin install {core.EGM_PLUGIN_ID}"
    plugin_dir = plugins / "cache" / core.EGM_MARKETPLACE / "egm" / version
    try:
        manifest = json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return f"the EGM plugin {version} is not in the plugin cache ({plugin_dir})"
    if manifest.get("version") != version:
        return f"the cached EGM plugin reports {manifest.get('version')!r}, not the pinned {version!r}"
    for persona in personas:
        adapter = plugin_dir / ".claude-plugin" / "agents" / core.ADAPTER_FILES[persona]
        try:
            text = adapter.read_text(encoding="utf-8")
        except OSError:
            return f"the EGM adapter for {persona!r} is missing ({adapter})"
        violations = core.adapter_isolation_violations(persona, text)
        if violations:
            return "; ".join(violations)
    return None


# --- paths -------------------------------------------------------------------


def _abs(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else (root / candidate)


def glossary_path(root: Path, slug: str) -> Path:
    return root / "_bmad-output" / "projects" / slug / "planning-artifacts" / "specs" / f"spec-{slug}" / "glossary.md"


def spec_path(root: Path, slug: str) -> Path:
    return glossary_path(root, slug).with_name("SPEC.md")


def dream_path(root: Path, slug: str) -> Path:
    return root / "docs" / "dreams" / f"{slug}.md"


def epics_path(root: Path, slug: str) -> Path:
    return root / "_bmad-output" / "projects" / slug / "planning-artifacts" / "epics.md"


def station_skill_path(root: Path, station: str) -> Path | None:
    name = long_form(station)
    for candidate in (
        root / ".claude" / "skills" / name / "active" / name / "SKILL.md",
        root / ".claude" / "skills" / name / "SKILL.md",
    ):
        if candidate.is_file():
            return candidate
    return None


def artifact_dir(root: Path, slug: str, config: core.ChallengeConfig) -> Path:
    return root / "_bmad-output" / "projects" / slug / config.artifact_dir


def default_standards(root: Path, slug: str, stage: str) -> tuple[Path, ...]:
    if stage in ("mint", "decompose", "rules"):
        return (root / CHAIN_STANDARD_RELPATH,)
    if stage == "readiness":
        return (root / STORY_SPEC_TEMPLATE_RELPATH,)
    return (spec_path(root, slug),)  # drift: the code is judged against the Spec


def build_context(
    root: Path,
    slug: str,
    stage: str,
    target: Path,
    config: core.ChallengeConfig,
    *,
    dream: Path | None = None,
) -> core.ChallengeContext:
    standards = tuple(_abs(root, s) for s in config.standards.get(stage, ())) or default_standards(root, slug, stage)
    return core.ChallengeContext(
        target=str(_abs(root, target)),
        glossary=str(glossary_path(root, slug)) if glossary_path(root, slug).is_file() else "",
        dream=str(dream or dream_path(root, slug)),
        standards=tuple(str(s) for s in standards),
    )


# --- journal -----------------------------------------------------------------


def _ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _utc_compact(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%S") + f"{moment.microsecond // 1000:03d}Z"


def append_journal(
    journal: Path,
    *,
    writer: str,
    counter: int,
    run_id: str,
    kind: str,
    phase: Phase,
    payload: Mapping[str, object],
    now: datetime,
    intent: JournalEntryId | None = None,
) -> JournalEntryId:
    entry_id = JournalEntryId(writer, counter)
    entry = build_entry(
        id=entry_id, ts=_ts(now), run_id=run_id, kind=kind, phase=phase, payload=dict(payload), intent_id=intent
    )
    prepared = prepare_for_write(entry)
    if prepared.sidecar_relative_path is not None:
        sidecar = journal.parent / prepared.sidecar_relative_path
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(prepared.sidecar_content or "", encoding="utf-8")
    with journal.open("a", encoding="utf-8") as handle:
        handle.write(prepared.line + "\n")
    return entry_id


def tree_snapshot(root: Path) -> str | None:
    """``git status --porcelain`` at ``root``; ``None`` when it is not a git tree."""
    try:
        done = PosixProcess().run(["git", "status", "--porcelain"], cwd=root, timeout_s=60)
    except ProcessError:
        return None
    return done.stdout if done.returncode == 0 else None


def journal_refusal(out_dir: Path, slug: str, reason: str, now: datetime) -> Path:
    """S6: a refusal is a journaled fact, not only a line on stderr."""
    run_id = mint_run_id(slug, _utc_compact(now), secrets.token_hex(4))
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    append_journal(
        run_dir / JOURNAL_FILENAME,
        writer=f"challenge-{secrets.token_hex(3)}",
        counter=0,
        run_id=run_id,
        kind=KIND_CHALLENGE_REFUSED,
        phase=Phase.OBSERVATION,
        payload={"project": slug, "reason": reason},
        now=now,
    )
    return run_dir


# --- one challenge -------------------------------------------------------------


def run_one(
    *,
    root: Path,
    slug: str,
    stage: str,
    target: Path,
    config: core.ChallengeConfig,
    runner: ChallengeRunner,
    out_dir: Path,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    dream: Path | None = None,
) -> RunOutcome:
    """Run one stage on one target. Refusals raise ``ChallengeRefused`` before
    anything is written; a session that fails or writes no valid report is an
    ``error`` on the outcome (unevaluable), never a finding."""
    context = build_context(root, slug, stage, target, config, dream=dream)
    violations = core.context_violations(context)
    if violations:
        raise ChallengeRefused("; ".join(violations))
    for path in (context.target, *context.context_paths()):
        if not Path(path).is_file():
            raise ChallengeRefused(f"{path} does not exist")
    moment = now()
    run_id = mint_run_id(slug, _utc_compact(moment), secrets.token_hex(4))
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    report_path = run_dir / REPORT_FILENAME
    journal = run_dir / JOURNAL_FILENAME
    personas = config.reviewers_for(stage)
    prompt = core.render_prompt(stage=stage, personas=personas, context=context, report_path=str(report_path))
    writer = f"challenge-{secrets.token_hex(3)}"
    intent = append_journal(
        journal,
        writer=writer,
        counter=0,
        run_id=run_id,
        kind=KIND_CHALLENGE_RUN,
        phase=Phase.INTENT,
        payload={
            "project": slug,
            "stage": stage,
            "target": context.target,
            "reviewers": [core.agent_type(p) for p in personas],
            "model": config.model,
            "plugin_version": config.plugin_version,
            "report": str(report_path),
        },
        now=moment,
    )
    error = ""
    report: core.ChallengeReport | None = None
    before = tree_snapshot(root)
    try:
        returncode = runner.run(
            prompt=prompt, model=config.model or None, cwd=root, log_path=run_dir / SESSION_LOG_FILENAME
        )
        if returncode != 0:
            error = f"challenge session exited {returncode}"
    except Exception as exc:  # the harness adapter's own error, or an OS failure
        error = f"challenge session did not run: {exc}"
    after = tree_snapshot(root)
    tree_changed = before is not None and after is not None and before != after
    if tree_changed and not error:
        error = "the challenge session changed the working tree; its report is not trusted"
    if not error:
        try:
            report = core.parse_report(report_path.read_text(encoding="utf-8"))
        except (OSError, core.ReportError) as exc:
            error = f"no valid report at {report_path}: {exc}"
    if report is not None:
        workspace = spec_path(root, slug).parent
        report = core.with_provenance(report, project=slug, spec_workspace=str(workspace))
        report_path.write_text(report.to_json() + "\n", encoding="utf-8")
    append_journal(
        journal,
        writer=writer,
        counter=1,
        run_id=run_id,
        kind=KIND_CHALLENGE_RUN,
        phase=Phase.OUTCOME,
        payload={
            "status": "error" if error else "reported",
            "error": error,
            "tree_changed": tree_changed,
            "findings": len(report.findings) if report else 0,
            "high": sum(1 for f in report.findings if f.severity == "high") if report else 0,
            "report": str(report_path),
        },
        now=now(),
        intent=intent,
    )
    return RunOutcome(run_id=run_id, run_dir=run_dir, report_path=report_path, report=report, error=error)


# --- drift (CAP-301) -----------------------------------------------------------

_EPIC_HEADING = re.compile(r"^## Epic (?P<n>\d+)\b")
_SPEC_LINE = re.compile(r"^\*\*Spec:\*\*\s*`(?P<path>[^`]+)`")
_SRC_PATH = re.compile(r"`(?P<path>src/[^`\s]+)`")


def epic_drift_paths(epics_text: str, epic: str) -> tuple[list[str], list[str]]:
    """The epic's story-spec paths and the ``src/`` paths its stories name."""
    specs: list[str] = []
    sources: list[str] = []
    inside = False
    for line in epics_text.splitlines():
        heading = _EPIC_HEADING.match(line)
        if heading:
            inside = heading.group("n") == str(epic)
            continue
        if inside and line.startswith("## "):
            inside = False
        if not inside:
            continue
        spec = _SPEC_LINE.match(line)
        if spec:
            specs.append(spec.group("path"))
        if line.startswith("**Surface:**"):
            sources.extend(m.group("path") for m in _SRC_PATH.finditer(line))
    return specs, sorted(dict.fromkeys(sources))


def write_drift_target(root: Path, slug: str, epic: str, out_dir: Path) -> Path:
    text = epics_path(root, slug).read_text(encoding="utf-8")
    specs, sources = epic_drift_paths(text, epic)
    if not specs:
        raise ChallengeRefused(f"epic {epic} has no story specs in {epics_path(root, slug)}")
    planning = epics_path(root, slug).parent
    lines = [f"# Drift target — {slug} epic {epic}", "", "## Story specs", ""]
    lines += [f"- {(planning.parent / s) if s.startswith('planning-artifacts/') else _abs(root, s)}" for s in specs]
    lines += ["", "## Source paths the stories name", ""]
    lines += [f"- {root / s}" for s in sources if (root / s).exists()] or ["- (none named)"]
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"drift-epic-{epic}.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


# --- audit (CAP-302) -------------------------------------------------------------


def audit_plan(root: Path) -> list[tuple[str, str, Path, Path | None]]:
    """``(project slug, stage, target, dream)`` for every audit run, in order:
    the repo rules first, then each station's Spec (mint) and epics (decompose)."""
    plan: list[tuple[str, str, Path, Path | None]] = [
        ("pyforge-marshal", "rules", root / "AGENTS.md", root / CHAIN_STANDARD_DREAM_RELPATH),
        ("pyforge-marshal", "rules", root / CHAIN_STANDARD_RELPATH, root / CHAIN_STANDARD_DREAM_RELPATH),
    ]
    for station in STATIONS:
        slug = long_form(station)
        skill = station_skill_path(root, station)
        if skill is not None:
            plan.append((slug, "rules", skill, None))
        plan.append((slug, "mint", spec_path(root, slug), None))
        plan.append((slug, "decompose", epics_path(root, slug), None))
    return plan


def run_audit(
    *,
    root: Path,
    config: core.ChallengeConfig,
    runner: ChallengeRunner,
    out_root: Path,
    force: bool,
    now: Callable[[], datetime],
) -> tuple[Path, dict[str, list[core.ChallengeReport]], list[str]]:
    audit_dir = out_root / f"audit-{now().date().isoformat()}"
    audit_dir.mkdir(parents=True, exist_ok=True)
    reports: dict[str, list[core.ChallengeReport]] = {}
    errors: list[str] = []
    audit_journal = audit_dir / JOURNAL_FILENAME
    writer = f"challenge-audit-{secrets.token_hex(3)}"
    counter = 0
    for slug, stage, target, dream in audit_plan(root):
        marker = audit_dir / f"{slug}.{stage}.{target.name}.json"
        if marker.is_file() and not force:
            try:
                reports.setdefault(slug, []).append(core.parse_report(marker.read_text(encoding="utf-8")))
            except OSError, core.ReportError:
                pass  # a corrupt marker is re-run below
            else:
                append_journal(
                    audit_journal,
                    writer=writer,
                    counter=counter,
                    run_id=audit_dir.name,
                    kind=KIND_AUDIT_SKIP,
                    phase=Phase.OBSERVATION,
                    payload={"project": slug, "stage": stage, "target": str(target), "marker": str(marker)},
                    now=now(),
                )
                counter += 1
                continue
        try:
            outcome = run_one(
                root=root,
                slug=slug,
                stage=stage,
                target=target,
                config=config,
                runner=runner,
                out_dir=audit_dir / "runs",
                now=now,
                dream=dream,
            )
        except ChallengeRefused as exc:
            errors.append(f"{slug} {stage} {target.name}: refused: {exc}")
            continue
        if outcome.report is None:
            errors.append(f"{slug} {stage} {target.name}: {outcome.error}")
            continue
        marker.write_text(outcome.report.to_json() + "\n", encoding="utf-8")
        reports.setdefault(slug, []).append(outcome.report)
    for slug, station_reports in reports.items():
        (audit_dir / f"{slug}.md").write_text(core.fleet_summary({slug: station_reports}), encoding="utf-8")
    (audit_dir / "fleet.md").write_text(core.fleet_summary(reports), encoding="utf-8")
    return audit_dir, reports, errors


# --- resolve (CAP-303) -------------------------------------------------------------


def append_memlog(root: Path, workspace: str, text: str) -> None:
    argv = [sys.executable, str(root / MEMLOG_SCRIPT_RELPATH), "append", "--workspace", workspace]
    try:
        done = PosixProcess().run([*argv, "--type", "event", "--text", text], cwd=root, timeout_s=60)
    except ProcessError as exc:
        raise core.ReportError(f"memlog append did not run: {exc}") from exc
    if done.returncode != 0:
        raise core.ReportError(f"memlog append failed: {done.stderr.strip() or done.stdout.strip()}")


def run_resolve(args: argparse.Namespace, *, root: Path, memlog: Callable[[Path, str, str], None]) -> int:
    require(EGM_RESOLVE_BRIDGE_FLAG_KEY)
    report_path = _abs(root, args.report)
    try:
        report = core.parse_report(report_path.read_text(encoding="utf-8"))
        accept = core.parse_id_notes(args.accept)
        reject = core.parse_id_notes(args.reject)
        resolution = core.resolve(report, accept=accept, reject=reject, report_path=str(report_path))
    except (OSError, core.ReportError) as exc:
        print(f"marshal factory challenge resolve: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if resolution.memlog_lines and not report.spec_workspace:
        print("marshal factory challenge resolve: the report names no owning Spec (spec_workspace)", file=sys.stderr)
        return EXIT_USAGE
    try:
        for line in resolution.memlog_lines:
            memlog(root, report.spec_workspace, line)
    except core.ReportError as exc:
        print(f"marshal factory challenge resolve: {exc}; the report is unchanged", file=sys.stderr)
        return EXIT_USAGE
    report_path.write_text(resolution.report.to_json() + "\n", encoding="utf-8")
    print(f"resolved: {len(accept)} accepted (memlog lines on {report.spec_workspace}), {len(reject)} rejected")
    if resolution.memlog_lines:
        print("next: re-derive the Spec with bmad-spec in the same change, so chain-currency reads both together")
    return EXIT_OK


# --- the handler -----------------------------------------------------------------


def run_challenge(
    args: argparse.Namespace,
    *,
    runner: ChallengeRunner | None = None,
    root: Path | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    memlog: Callable[[Path, str, str], None] = append_memlog,
) -> int:
    require(EGM_CHALLENGE_FLAG_KEY)
    root = root or _default_repo_root()
    if getattr(args, "challenge_command", None) == "resolve":
        return run_resolve(args, root=root, memlog=memlog)
    require(EGM_POLICY_BLOCK_FLAG_KEY)
    try:
        return _run(args, runner=runner, root=root, now=now)
    except ChallengeRefused as exc:
        print(f"marshal factory challenge: {exc}", file=sys.stderr)
        return EXIT_USAGE


def _run(args: argparse.Namespace, *, runner: ChallengeRunner | None, root: Path, now: Callable[[], datetime]) -> int:
    slug = args.project or ("pyforge-marshal" if args.audit else None)
    if not slug:
        raise ChallengeRefused("--project is required")
    effective = compose_effective(slug)
    config = challenge_config(effective)
    if not config.enabled:
        raise ChallengeRefused(f"the challenger is off for {slug}: no enabled [challenge] block")
    refusals = core.render_refusals(
        config,
        session_models=session_models(effective),
        model_cost_catalog=effective.model_cost_catalog.value
        if isinstance(effective.model_cost_catalog.value, Mapping)
        else {},
    )
    if refusals:
        raise ChallengeRefused("; ".join(refusals))
    if args.audit:
        require(EGM_AUDIT_FLAG_KEY)
    elif args.stage == "drift":
        require(EGM_RETRO_DRIFT_FLAG_KEY)
    plugins = plugins_root()
    personas = tuple(dict.fromkeys(p for stage in core.STAGES for p in config.reviewers_for(stage)))
    refusal = plugin_refusal(root, plugins, config.plugin_version, personas)
    if refusal:
        journal_refusal(artifact_dir(root, slug, config), slug, refusal, now())
        raise ChallengeRefused(refusal)
    if runner is None:
        from ..adapters.challenge_harness import ClaudeChallengeRunner

        runner = ClaudeChallengeRunner(plugins_root=plugins)
    out_root = artifact_dir(root, slug, config)
    if args.audit:
        audit_dir, reports, errors = run_audit(
            root=root, config=config, runner=runner, out_root=out_root, force=args.force, now=now
        )
        total = sum(len(r.findings) for rs in reports.values() for r in rs)
        _emit(args, {"audit_dir": str(audit_dir), "stations": len(reports), "findings": total, "errors": errors})
        return exit_code_for(Verdict.UNEVALUABLE) if errors and not reports else EXIT_OK
    if not args.stage:
        raise ChallengeRefused("--stage is required (or --audit)")
    if args.stage == "drift":
        if not args.epic:
            raise ChallengeRefused("--stage drift needs --epic <n>")
        target = write_drift_target(root, slug, args.epic, out_root / "drift")
    elif args.target:
        target = _abs(root, args.target)
    else:
        raise ChallengeRefused("--target is required for this stage")
    outcome = run_one(
        root=root, slug=slug, stage=args.stage, target=target, config=config, runner=runner, out_dir=out_root, now=now
    )
    _emit(
        args,
        {
            "run_id": outcome.run_id,
            "report": str(outcome.report_path),
            "findings": len(outcome.report.findings) if outcome.report else 0,
            "error": outcome.error,
        },
    )
    return exit_code_for(Verdict.UNEVALUABLE) if outcome.error else EXIT_OK


def _emit(args: argparse.Namespace, data: Mapping[str, object]) -> None:
    if getattr(args, "format", "text") == "json":
        print(json.dumps(dict(data), sort_keys=True))
        return
    for key, value in data.items():
        print(f"{key}: {value}")


# --- the dispatch hook (CAP-300) -----------------------------------------------------


@dataclass(frozen=True)
class ReadinessResult:
    """What the dispatch hook journals and reports. ``ran`` is False when the
    hook is off; then dispatch proceeds byte-identically."""

    ran: bool
    report_path: str = ""
    findings: int = 0
    high: int = 0
    error: str = ""


def readiness_for_dispatch(
    *,
    root: Path,
    slug: str,
    story_spec: Path,
    effective: policy.EffectivePolicy,
    runner: ChallengeRunner | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    plugins: Path | None = None,
) -> ReadinessResult:
    """Run the readiness stage before a dispatch's harness launches, when the
    switch is on and the station's block names the stage. Report only: never a
    status move, never a ledger write, never a refusal of the dispatch."""
    if not flag_on(EGM_CHALLENGE_FLAG_KEY) or not flag_on(EGM_DISPATCH_READINESS_FLAG_KEY):
        return ReadinessResult(ran=False)
    config = challenge_config(effective)
    if not config.stage_on("readiness"):
        return ReadinessResult(ran=False)
    one = core.ChallengeConfig(
        enabled=True,
        stages=("readiness",),
        reviewers={"readiness": ("implementation-readiness",)},
        model=config.model,
        standards=dict(config.standards),
        artifact_dir=config.artifact_dir,
        plugin_version=config.plugin_version,
    )
    refusals = core.render_refusals(
        one,
        session_models=session_models(effective),
        model_cost_catalog=effective.model_cost_catalog.value
        if isinstance(effective.model_cost_catalog.value, Mapping)
        else {},
    )
    plugins = plugins or plugins_root()
    refusal = "; ".join(refusals) or plugin_refusal(root, plugins, one.plugin_version, ("implementation-readiness",))
    if refusal:
        return ReadinessResult(ran=True, error=f"readiness challenge refused: {refusal}")
    if runner is None:
        from ..adapters.challenge_harness import ClaudeChallengeRunner

        runner = ClaudeChallengeRunner(plugins_root=plugins)
    try:
        outcome = run_one(
            root=root,
            slug=slug,
            stage="readiness",
            target=story_spec,
            config=one,
            runner=runner,
            out_dir=artifact_dir(root, slug, one),
            now=now,
        )
    except ChallengeRefused as exc:
        return ReadinessResult(ran=True, error=f"readiness challenge refused: {exc}")
    if outcome.report is None:
        return ReadinessResult(ran=True, report_path=str(outcome.report_path), error=outcome.error)
    return ReadinessResult(
        ran=True,
        report_path=str(outcome.report_path),
        findings=len(outcome.report.findings),
        high=sum(1 for f in outcome.report.findings if f.severity == "high"),
    )


def readiness_payload(result: ReadinessResult) -> dict[str, object]:
    return {
        "report": result.report_path,
        "findings": result.findings,
        "high": result.high,
        "error": result.error,
    }
