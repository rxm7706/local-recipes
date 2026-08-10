#!/usr/bin/env python3
"""Mutation-only residual: ground-truth facts, the `--specs` status report,
`--fix`, and `--write-baseline` for the local-recipes BMAD project docs.

Story 6.9 ("the `scripts/` shims retire") ported this script's own
read-only VERDICT — the 18 finding kinds across pin currency, archive
hygiene, spec/deferred-work staleness, count/phase-list staleness, stale
rule content, sync-baseline drift, project coverage, Tier-1/Tier-3
alignment, spec indexing, and Dream vocabulary/ownership — into
`pyforge.doctor.sources.factory::gather`
(`python -m pyforge.doctor.sources bmad-drift`). That port is the one
place the verdict lives now; this file is NOT a detector any more (no
`DETECTOR = {...}` marker). Renamed from `bmad_drift_check.py` in review
pass 2 for the same reason: `scripts/detectors.py::discover()` globs
`scripts/*_check.py` and hard-fails on ANY match with no valid
`DETECTOR = {...}`, so a markerless file whose name still matched that
glob was itself a permanent registry finding — invisible to the AST scan
was not enough; the name had to stop matching the pattern.

What survives here, and why it could not simply move with the rest: Doctor
sources are deliberately READ-ONLY gathers (Charter §6 — the producing
station keeps the operational guard; only Doctor holds the verdict), so
`factory.gather` never got a `--fix`/`--write-baseline` mutation path or
the `--specs`/`--json` reporting modes, and nothing else in the repo has
them either. All four are live and depended on today —
`_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md`, `CLAUDE.md`'s own
Sync-loop section (which documents `--specs` by name), and the plain
`python scripts/bmad_drift_reconcile.py --fix`/`--write-baseline` workflow
below all instruct real, working commands — NOT the `bmad-drift-check`/
`bmad-groundtruth` pixi tasks, which invoke the read-only dispatcher and
do not understand any of these flags. So they stay here:

  --json / --groundtruth   print live ground-truth facts (unchanged)
  --specs                  report each docs/specs intake spec's status +
                            whether CLAUDE.md indexes it (unchanged)
  --fix                    apply the safe mechanical remediations (archive
                            moves, stray-file removal) (unchanged)
  --write-baseline         stamp .sync-baseline.json to the current state,
                            for `run_checks()`'s successor
                            (`factory.gather`) to compare against next time
                            (unchanged)

`classify()` (the filing-convention classifier) and the `TRACKED`
doc-category table are also carried over verbatim, even though nothing in
THIS reduced file still calls them: `sources/factory.py` ported an
identical copy for its own coverage/pin checks, and SYNC-RUNBOOK.md's
extension pointers (a new artifact shape needs a new `classify()` rule)
name this file as the reference copy. Kept in sync by hand; there is no
mechanism enforcing the two agree.

Usage (plain `python`, no pixi task -- the `bmad-drift-check`/`bmad-groundtruth`
pixi tasks invoke the dispatcher below instead, which does not understand any of
these flags):
  python scripts/bmad_drift_reconcile.py --fix
  python scripts/bmad_drift_reconcile.py --write-baseline
  python scripts/bmad_drift_reconcile.py --json    # or --groundtruth, same output
  python scripts/bmad_drift_reconcile.py --specs
Verdict (the 18 finding kinds, unchanged behavior):
  pixi run -e local-recipes bmad-drift-check
  python -m pyforge.doctor.sources bmad-drift
See _bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md for the full re-sync procedure.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL = REPO_ROOT / ".claude" / "skills" / "conda-forge-expert"
# The factory document set moved local-recipes -> pyforge-marshal on 2026-07-28: the
# placeholder project dissolved under Charter §5, and this doc set IS the factory rebuild
# spec, owned by Marshal via the regenerable-factory practice. TRACKED below uses paths
# RELATIVE to PROJ, so retargeting this one constant carried all 18 of them.
PROJ = REPO_ROOT / "_bmad-output" / "projects" / "pyforge-marshal"
PLAN = PROJ / "planning-artifacts"
IMPL = PROJ / "implementation-artifacts"
BASELINE = PROJ / ".sync-baseline.json"  # records the repo state artifacts were last reconciled against
DOCS_SPECS = REPO_ROOT / "docs" / "specs"  # Tier-1: BMAD-consumable intake specs (bmad-quick-dev entry points)

Ver = tuple[int, int, int]

# Tracked pinned docs and their sync category -- kept for `classify()` below (its own
# `tracked:<category>` branch), not read by anything else in this reduced file.
TRACKED: list[tuple[str, str]] = [
    ("planning-artifacts/index.md", "living"),
    ("planning-artifacts/architecture.md", "living"),
    ("planning-artifacts/architecture-cf-atlas.md", "living"),
    ("planning-artifacts/architecture-conda-forge-expert.md", "living"),
    ("planning-artifacts/architecture-mcp-server.md", "living"),
    ("planning-artifacts/architecture-bmad-infra.md", "living"),
    ("planning-artifacts/integration-architecture.md", "living"),
    ("planning-artifacts/development-guide.md", "living"),
    ("planning-artifacts/deployment-guide.md", "living"),
    ("planning-artifacts/source-tree-analysis.md", "living"),
    ("planning-artifacts/project-overview.md", "living"),
    ("planning-artifacts/project-parts.json", "living"),
    ("project-context.md", "context"),
    ("planning-artifacts/PRD.md", "plan"),
    ("planning-artifacts/epics-regenerable-factory.md", "plan"),  # renamed on the move: marshal keeps its own epics.md
    ("planning-artifacts/implementation-readiness-report.md", "snapshot"),  # dated gate output, regenerated not pinned
    ("planning-artifacts/validation-report-PRD.md", "snapshot"),
]
TRACKED_CAT = dict(TRACKED)
TRACKED_REL = set(TRACKED_CAT)
CONFIG_FILES = {".bmad-config.toml",            # config, not pin-synced — but must be accounted-for
                ".bmad-config.user.toml"}       # layer 6 of the config merge; gitignored, per-user
IGNORE_PARTS = {"__pycache__"}

STRAY_SUFFIXES = {".patch", ".diff", ".bak", ".orig", ".tmp", ".rej"}

_VER_RE = re.compile(r"\*\*v(\d+)\.(\d+)\.(\d+)\*\*")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _rel(path: Path) -> str:
    for base in (PROJ, REPO_ROOT):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return str(path)


# ---------------------------------------------------------------- ground truth
def skill_version() -> str | None:
    m = _VER_RE.search(_read(SKILL / "CHANGELOG.md"))
    return f"{m.group(1)}.{m.group(2)}.{m.group(3)}" if m else None


def schema_version() -> int | None:
    m = re.search(r"SCHEMA_VERSION\s*=\s*(\d+)", _read(SKILL / "scripts" / "conda_forge_atlas.py"))
    return int(m.group(1)) if m else None


def mcp_tool_count() -> int:
    return _read(REPO_ROOT / ".claude" / "tools" / "conda_forge_server.py").count("@mcp.tool")


def phase_ids() -> list[str]:
    """Top-level + sub phase IDs from the PHASES registry, e.g. ['B','B.5',...,'O','P',...]."""
    text = _read(SKILL / "scripts" / "conda_forge_atlas.py")
    m = re.search(r"PHASES\s*[:=].*?\[(.*?)\n\]", text, re.S)
    return re.findall(r'\(\s*"([^"]+)"', m.group(1)) if m else []


def phase_count() -> int:
    """Executable pipeline phases — from the PHASES registry, the authoritative list."""
    return len(phase_ids())


def max_single_phase() -> str:
    singles = [p for p in phase_ids() if re.fullmatch(r"[A-Z]", p)]
    return max(singles) if singles else "N"


def gotcha_max() -> int | None:
    nums = [int(n) for n in re.findall(r"^###\s+G(\d+)", _read(SKILL / "SKILL.md"), re.M)]
    return max(nums) if nums else None


def env_count() -> int:
    out, in_block = 0, False
    for line in _read(REPO_ROOT / "pixi.toml").splitlines():
        if line.strip() == "[environments]":
            in_block = True
            continue
        if in_block:
            if line.startswith("["):
                break
            if "=" in line and not line.lstrip().startswith("#"):
                out += 1
    return out


def recipe_split() -> dict[str, int]:
    # Churny: changes constantly during the v0->v1 migration. Informational only, never gated.
    recipes = REPO_ROOT / "recipes"
    if not recipes.is_dir():
        return {"dirs": 0, "recipe_yaml": 0, "meta_yaml": 0}
    return {
        "dirs": len([p for p in recipes.iterdir() if p.is_dir()]),
        "recipe_yaml": len(list(recipes.glob("*/recipe.yaml"))),
        "meta_yaml": len(list(recipes.glob("*/meta.yaml"))),
    }


def ground_truth() -> dict:
    return {
        "skill_version": skill_version(),
        "schema_version": schema_version(),
        "mcp_tools": mcp_tool_count(),
        "atlas_phases": phase_count(),
        "gotcha_max": gotcha_max(),
        "pixi_envs": env_count(),
        "recipes_churny": recipe_split(),
    }


# -------------------------------------------------------------- sync baseline
# The baseline is the closed-loop anchor: it records the source-of-truth SURFACE the artifacts
# were last reconciled against, so the detector (now `factory.gather`) trips on ANY
# out-of-band change (BMAD or not), not just the specific counts the checks hardcode.
FINGERPRINT_KEYS = ("skill_version", "schema_version", "mcp_tools", "atlas_phases",
                    "gotcha_max", "pixi_envs", "phase_ids")


def git_head() -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None
    except Exception:
        return None


def fingerprint() -> dict:
    gt = ground_truth()
    fp = {k: gt[k] for k in FINGERPRINT_KEYS if k in gt}
    fp["phase_ids"] = phase_ids()
    fp["git_head"] = git_head()
    return fp


# ----------------------------------------------------------------- doc parsing
def frontmatter_status(path: Path) -> str | None:
    """The neutral `status:` from a spec's YAML frontmatter (framework-agnostic source of truth)."""
    text = _read(path)
    parts = text.split("---", 2)
    fm = parts[1] if len(parts) >= 3 and text.lstrip().startswith("---") else text[:600]
    m = re.search(r"^\s*status\s*:\s*([A-Za-z-]+)", fm, re.M)
    return m.group(1).lower() if m else None


def classify(path: Path) -> str:
    """Filing-convention classifier -- carried verbatim, uncalled within
    this reduced file (its sole caller, `check_coverage`, moved to
    `sources/factory.py`). See the module docstring."""
    rel = _rel(path)
    if any(part in IGNORE_PARTS for part in path.parts):
        return "ignored"
    if rel in CONFIG_FILES:
        return "config"
    if rel == ".sync-baseline.json":
        return "baseline"
    if rel == "SYNC-RUNBOOK.md":
        return "runbook"
    if rel == "project-context.md":
        return "tracked:context"
    if rel in TRACKED_REL:
        return f"tracked:{TRACKED_CAT[rel]}"
    if rel.startswith("planning-artifacts/change-history/"):
        return "archive:change-history"
    # --- the 6.10 sharded station shape -------------------------------------
    # Added 2026-07-28 when this detector was retargeted from the dissolved
    # `local-recipes` placeholder onto `pyforge-marshal`. It had only ever seen one
    # project's shape; a station carries its OWN chain artifacts too — sharded PRD and
    # architecture run folders, per-chain epics, briefs, upstream reports. Fourteen files
    # landed as `uncovered` on the first run, which is the coverage rule working: an
    # unclassified file is a hole, not a pass.
    if re.fullmatch(r"planning-artifacts/prds/prd-[a-z0-9-]+-\d{4}-\d{2}-\d{2}/[A-Za-z0-9._-]+", rel):
        return "tracked:plan"          # bmad-prd run folder: prd.md + memlog + reviews
    if re.fullmatch(r"planning-artifacts/architecture/architecture-[a-z0-9-]+-\d{4}-\d{2}-\d{2}/.*", rel):
        return "tracked:plan"          # bmad-architecture run folder (incl. reviews/)
    if re.fullmatch(r"planning-artifacts/briefs/brief-[a-z0-9-]+-\d{4}-\d{2}-\d{2}/[A-Za-z0-9._-]+", rel):
        return "tracked:plan"
    if re.fullmatch(r"planning-artifacts/epics(-[a-z0-9-]+)?\.md", rel):
        # The station's own epics.md, plus chain-scoped epics-<slug>.md for chains that
        # moved in under Charter §5 (the destination keeps its own epics.md).
        return "tracked:plan"
    if re.fullmatch(r"planning-artifacts/product-brief-[a-z0-9-]+\.md", rel):
        return "tracked:plan"
    if re.fullmatch(r"planning-artifacts/research/[A-Za-z0-9._-]+\.md", rel):
        return "archive:research"      # undated research + briefs filed under research/
    if re.fullmatch(r"planning-artifacts/upstream-report-[a-z0-9-]+\.md", rel):
        return "archive:change-history"  # frozen upstream defect report
    if re.fullmatch(r"planning-artifacts/implementation-readiness-report-\d{4}-\d{2}-\d{2}\.md", rel):
        # A dated re-run of the readiness gate alongside the undated TRACKED one (line ~84).
        # Not pin-gated by this rule, same as sharded prd/arch/epics — a future re-run needs
        # no new TRACKED entry to stay covered.
        return "tracked:snapshot"
    if rel == "planning-artifacts/README.md":
        return "tracked:living"
    # --- shapes that landed as `uncovered` on 2026-08-08 ----------------------
    # Same lesson as the 6.10 sharding block above: an unclassified file is a hole,
    # not a pass. These eleven were the standing HARD findings that made
    # test_bmad_artifacts_integrity red.
    if rel == "README.md":
        # The station's own README (`# PyForge Station: <slug>`) — hand-maintained
        # orientation for the project dir, sibling of planning-artifacts/README.md.
        return "tracked:living"
    if rel == "planning-artifacts/specs/README.md":
        # The story-spec index that documents the tracked/durable spec convention
        # (specs survive worktree teardown). Hand-authored prose, not pin-gated.
        return "tracked:living"
    if rel == "planning-artifacts/test-architecture.md":
        # bmad test-architecture output — a chain artifact alongside prd/architecture,
        # so it classifies with them rather than earning its own category.
        return "tracked:plan"
    if rel == "planning-artifacts/upstream-register.json":
        # Marshal's hand-curated register of upstream bmad-loop gaps + workarounds
        # (FR-58/AD-2), read by `marshal upstream`. Curated data, so git review — not
        # a version pin — decides content changes.
        return "tracked:register"
    if re.fullmatch(r"implementation-artifacts/epic-\d+-retro-\d{4}-\d{2}-\d{2}\.md", rel):
        # Dated per-epic retros written at the implementation-artifacts ROOT. The
        # pre-existing rule only matched the retros/ subdir, so these fell through.
        return "archive:retros"
    if re.fullmatch(r"implementation-artifacts/runs/[A-Za-z0-9._-]+/.*", rel):
        # bmad-loop run records (journal.jsonl et al) — Tier-3, gitignored, written by
        # the engine per run. Never hand-edited and never pin-gated.
        return "local:run-journal"
    if re.fullmatch(r"implementation-artifacts/epic-\d+-context\.md", rel):
        return "local:sprint-feed"     # Tier-3 story context, gitignored
    if re.fullmatch(r"planning-artifacts/prfaq-[a-z0-9-]+(-distillate)?\.md", rel):
        # PRFAQ kill-test records + distillates (bmad-prfaq): frozen stress-test
        # outputs — no pin gating.
        return "archive:prfaq"
    if re.fullmatch(r"planning-artifacts/campaign-[a-z0-9-]+-\d{4}-\d{2}-\d{2}\.md", rel):
        # Campaign records (a dated, program-scale effort across many projects —
        # e.g. the 2026-07-25 spec-completion campaign): frozen after the campaign
        # closes, like a retro. Historical account, so no pin gating.
        return "archive:campaign"
    if re.fullmatch(r"planning-artifacts/research/[a-z0-9-]+-research-\d{4}-\d{2}-\d{2}\.md", rel):
        # Research reports (bmad-domain/market/technical-research skills, plus
        # backfilled distillations): dated point-in-time snapshots — never
        # re-grounded, so no pin gating.
        return "archive:research"
    if re.fullmatch(r"planning-artifacts/specs/spec-[a-z0-9-]+/[A-Za-z0-9._-]+\.md", rel):
        # bmad-spec output folders: SPEC.md (the Spec) + append-only .memlog.md
        # + companions. The memlog is the decision-of-record and SPEC.md re-derives
        # from it (never hand-patched), so no pin gating here.
        return "tracked:spec"
    if re.fullmatch(r"planning-artifacts/specs/spec-[a-z0-9-]+\.md", rel):
        # FLAT spec files directly under specs/ — the rule above only matched spec
        # FOLDERS, so a flat one fell through to UNKNOWN and failed coverage. Two
        # real shapes live here: per-story specs (the durable Tier-2 home) and
        # standalone effort specs such as the 2026-07-26 code-audit remediation
        # record. Both are tracked, hand-authored, and not pin-gated.
        return "tracked:spec"
    if rel.startswith("implementation-artifacts/retros/"):
        return "archive:retros"
    if rel == "implementation-artifacts/deferred-work.md":
        return "tracked:deferred"
    if rel == "planning-artifacts/deferred-work-ledger.md":
        # The DURABLE twin of the Tier-3 ledger above, promoted 2026-07-29 because
        # bmad-loop's follow-up-review damping refiles into the gitignored one. Hand-authored
        # and not pin-gated: entries are dated in their own bodies, and the file is
        # deliberately a copy whose curation lags — a version pin would report drift on
        # every skill bump for a document that tracks stories, not the skill surface.
        return "tracked:deferred"
    if re.fullmatch(r"implementation-artifacts/sprint-status(-[a-z0-9-]+)?\.yaml", rel):
        # Tier-3 sprint feed (gitignored, local-only) — the program console's
        # dashboard-gen reads it; no pin gating.
        return "local:sprint-feed"
    if rel == "planning-artifacts/marshal-policy.toml":
        # Marshal's PROJECT-POLICY layer -- the middle tier of AD-16's
        # defaults -> project -> flags chain, added 2026-07-30. Tracked on
        # purpose: it is the governed SOURCE the gitignored, derived
        # `.bmad-loop/policy.toml` is rendered from (AD-12/AD-35), so a fresh
        # clone or a newly provisioned loop home can reproduce its harness
        # policy. Hand-authored and not pin-gated -- it carries a station's
        # verify command and gate posture, which track that project's own
        # surface rather than the skill's.
        return "tracked:marshal-policy"
    if rel == "planning-artifacts/sprint-status-ledger.yaml":
        # The DURABLE twin of the Tier-3 sprint feed above, promoted 2026-07-30 for
        # the same reason as deferred-work-ledger.md: implementation-artifacts/ is
        # gitignored wholesale, so the only record that a story finished was
        # invisible to CI, which is why the console's deploy-time render had to
        # reconstruct DONE from commit subjects — and why it broke when squash
        # merging left a bmad-loop merge subject unreachable from main.
        # GENERATED by scripts/promote_sprint_status.py (`sprint-ledger-sync`) and
        # read by docs/dashboard/generate.py:apply_tracked_ledger; freshness is
        # enforced against the Tier-3 feed by the drift verdict, not by a version
        # pin — it tracks stories, not the skill surface.
        return "tracked:sprint-ledger"
    if re.fullmatch(r"implementation-artifacts/spec-.*\.md", rel):
        return "tracked:spec"
    return "UNKNOWN"


# ----------------------------------------------------------------------- fix
def _post_fix_verdict() -> tuple[int, list | None]:
    """Re-derive the REAL post-``--fix`` verdict via the ported source, install-free
    the same way ``scripts/spec_surface_reconcile.py`` reaches ``gather_spec_surface``
    (review pass 2): mechanical remediation alone does not make the drift verdict
    clean (most findings this script's `--fix` never touched -- pin currency, stale
    rules, count/phase-list drift, ... -- are untouched by design), so the caller
    must re-check, not assume. Returns ``(exit_code, findings_or_None)``; ``None``
    findings means the re-check itself could not run (missing `pyforge.doctor`, e.g.
    PyYAML absent for one of its transitive imports) -- reported honestly, never
    folded into a false 0.
    """
    doctor_src = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"
    if str(doctor_src) not in sys.path:
        sys.path.insert(0, str(doctor_src))
    try:
        from pyforge.doctor.sources import factory as doctor_factory
        from pyforge.doctor.verdict import exit_code_for
    except ImportError as exc:
        print(
            f"WARNING: cannot re-verify the post-fix state here -- {exc}. "
            f"Run `python -m pyforge.doctor.sources bmad-drift` by hand to confirm "
            f"nothing real remains.",
            file=sys.stderr,
        )
        return 2, None
    findings = doctor_factory.gather(REPO_ROOT)
    return exit_code_for(findings), findings


def do_fix() -> list[str]:
    actions = []
    if PLAN.is_dir():
        misplaced = list(PLAN.glob("sprint-change-proposal-*.md"))
        if misplaced:
            (PLAN / "change-history").mkdir(exist_ok=True)
            for p in misplaced:
                p.rename(PLAN / "change-history" / p.name)
                actions.append(f"moved {p.name} -> change-history/")
    if IMPL.is_dir():
        retros = list(IMPL.glob("retro-*.md"))
        if retros:
            (IMPL / "retros").mkdir(exist_ok=True)
            for p in retros:
                p.rename(IMPL / "retros" / p.name)
                actions.append(f"moved {p.name} -> retros/")
        for p in list(IMPL.iterdir()):
            if p.is_file() and p.suffix in STRAY_SUFFIXES:
                p.unlink()
                actions.append(f"removed stray {p.name}")
    return actions


# --------------------------------------------------------------------- output
def cmd_json() -> int:
    print(json.dumps(ground_truth(), indent=2))
    return 0


def cmd_specs() -> int:
    """Report each Tier-1 intake spec's neutral status + whether it's indexed in CLAUDE.md."""
    if not DOCS_SPECS.is_dir():
        print(f"no docs/specs/ at {DOCS_SPECS}", file=sys.stderr)
        return 0
    claude = _read(REPO_ROOT / "CLAUDE.md")
    specs = sorted(DOCS_SPECS.glob("*.md"))
    w = max((len(p.name) for p in specs), default=4)
    print(f"docs/specs intake specs ({len(specs)}) — status is the framework-neutral source of truth\n")
    print(f"  {'SPEC'.ljust(w)}  {'STATUS':<12} INDEXED")
    print(f"  {'-' * w}  {'-' * 12} -------")
    by_status: dict[str, int] = {}
    for p in specs:
        st = frontmatter_status(p) or "(none)"
        by_status[st] = by_status.get(st, 0) + 1
        print(f"  {p.name.ljust(w)}  {st:<12} {'yes' if p.name in claude else 'NO'}")
    print("\n  totals: " + "  ".join(f"{k}={v}" for k, v in sorted(by_status.items())))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--json", "--groundtruth", action="store_true", dest="json",
                   help="print live ground-truth facts as JSON")
    g.add_argument("--specs", action="store_true",
                   help="report each docs/specs intake spec's status + CLAUDE.md index state")
    ap.add_argument("--fix", action="store_true",
                    help="apply safe mechanical remediations (archive moves, stray-file removal)")
    ap.add_argument("--write-baseline", action="store_true",
                    help="stamp .sync-baseline.json to the current state (run after a reconciliation)")
    args = ap.parse_args(argv)
    if not PROJ.is_dir():
        print(f"BMAD project not found at {PROJ} — nothing to do.", file=sys.stderr)
        return 0
    if args.json:
        return cmd_json()
    if args.specs:
        return cmd_specs()
    if args.write_baseline:
        BASELINE.write_text(json.dumps(fingerprint(), indent=2) + "\n", encoding="utf-8")
        fp = fingerprint()
        print(f"baseline written: {_rel(BASELINE)} @ git {fp.get('git_head')} / skill v{fp.get('skill_version')}")
        return 0
    if args.fix:
        actions = do_fix()
        print("FIX applied:" if actions else "FIX: nothing to remediate.")
        for a in actions:
            print(f"  - {a}")
        code, findings = _post_fix_verdict()
        if findings is not None:
            gating = [f for f in findings if f.status.value == "fail"]
            if gating:
                print(f"\npost-fix verdict: {len(gating)} finding(s) remain (fix only "
                      f"handles archive-misplaced/stray-file; everything else needs a "
                      f"real reconciliation):")
                for f in gating:
                    print(f"  [{f.check}] {f.status.value} -- {f.message}")
            else:
                print("\npost-fix verdict: clean.")
        return code
    print(
        "this script no longer computes the drift verdict -- run "
        "`python -m pyforge.doctor.sources bmad-drift` for that. Pass --json/"
        "--groundtruth, --specs, --fix, or --write-baseline for this script's "
        "remaining mutation/reporting surface.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
