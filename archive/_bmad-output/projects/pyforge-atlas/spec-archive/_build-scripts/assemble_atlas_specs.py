#!/usr/bin/env python3
"""Assemble every BMAD spec used to build pyforge-atlas into one markdown file."""
from pathlib import Path
import datetime

ROOT = Path("/home/user/local-recipes")
PA = ROOT / "_bmad-output/projects/pyforge-atlas/planning-artifacts"
IA = ROOT / "_bmad-output/projects/pyforge-atlas/implementation-artifacts"
OUT = Path("/tmp/claude-0/-home-user-local-recipes/8c301a61-5446-55e6-b085-93ba3871f3dc/scratchpad/ATLAS-BMAD-SPECS-CONSOLIDATED.md")

# (section-title, tier-label, source-path, fence-lang-or-None)
SECTIONS = [
    # Tier 1 — intake spec
    ("Intake spec (Tier 1 — the binding contract)", "Tier 1",
     ROOT / "docs/specs/cfe-atlas-datapipeline-kedro-migration.md", None),
    # Tier 2 — planning
    ("Intake groundtruth", "Tier 2", PA / "intake-groundtruth-2026-07-17.md", None),
    ("PRD", "Tier 2", PA / "prds/prd-pyforge-atlas-2026-07-17/prd.md", None),
    ("PRD addendum", "Tier 2", PA / "prds/prd-pyforge-atlas-2026-07-17/addendum.md", None),
    ("Architecture spine", "Tier 2",
     PA / "architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md", None),
    ("Epics & stories (all 9 epics / 32 stories)", "Tier 2", PA / "epics.md", None),
    ("Agents & skills record", "Tier 2", PA / "agents-and-skills.md", None),
    ("Implementation-readiness gate report", "Tier 2",
     PA / "implementation-readiness-report-2026-07-17.md", None),
    ("Sprint-change proposal", "Tier 2", PA / "sprint-change-proposal-2026-07-17.md", None),
    ("Planning-phase closeout", "Tier 2", PA / "planning-phase-closeout-2026-07-17.md", None),
    # Tier 3 — story specs (local-only; only waves 0/A/B exist as files)
    ("Story 0.1 — legacy contextual skill", "Tier 3", IA / "0-1-generate-legacy-contextual-skill.md", None),
    ("Story A1 — scaffold Kedro/pixi project", "Tier 3", IA / "a1-scaffold-the-kedro-pixi-project-via-nebi.md", None),
    ("Story A2 — data catalog", "Tier 3", IA / "a2-define-the-data-catalog-for-all-sources-outputs.md", None),
    ("Story A3 — IncrementalParquetDataset / TTL", "Tier 3", IA / "a3-implement-incrementalparquetdataset-for-ttl-gating.md", None),
    ("Story B1 — conda-side backbone phases", "Tier 3", IA / "b1-port-the-conda-side-backbone-phases-into-kedro-nodes.md", None),
    ("Story B2 — PyPI + vulnerability pipelines", "Tier 3", IA / "b2-port-the-pypi-and-vulnerability-pipelines.md", None),
    ("Story B3 — Kedro-API-native MCP tools", "Tier 3", IA / "b3-re-expose-the-data-surface-as-kedro-api-native-mcp-tools.md", None),
    ("Story B4 — dataset parity vs legacy", "Tier 3", IA / "b4-verify-dataset-parity-against-the-legacy-orchestrator.md", None),
    ("Story B5 — external-refresh assets", "Tier 3", IA / "b5-port-the-external-refresh-assets.md", None),
    ("Story B6 — seed-gaps pipeline", "Tier 3", IA / "b6-port-the-seed-gaps-pipeline.md", None),
    ("Story B7 — universal SBOM intake", "Tier 3", IA / "b7-extend-the-universal-sbom-intake.md", None),
    ("Story B8 — Basilisk vuln ingestion", "Tier 3", IA / "b8-basilisk-conda-native-vulnerability-ingestion.md", None),
    ("Deferred-work ledger", "Tier 3", IA / "deferred-work.md", None),
    ("Sprint status", "Tier 3", IA / "sprint-status.yaml", "yaml"),
]

# process artifacts we index but do not inline
APPENDIX = [
    PA / "prds/prd-pyforge-atlas-2026-07-17/validation-report.md",
    PA / "prds/prd-pyforge-atlas-2026-07-17/review-adversarial-general.md",
    PA / "prds/prd-pyforge-atlas-2026-07-17/review-rubric.md",
    PA / "prds/prd-pyforge-atlas-2026-07-17/.memlog.md",
    PA / "architecture/architecture-pyforge-atlas-2026-07-17/reviews/reconcile-inputs.md",
    PA / "architecture/architecture-pyforge-atlas-2026-07-17/reviews/review-adversarial-two-units.md",
    PA / "architecture/architecture-pyforge-atlas-2026-07-17/reviews/review-rubric-walker.md",
    PA / "architecture/architecture-pyforge-atlas-2026-07-17/reviews/review-version-verification.md",
    PA / "architecture/architecture-pyforge-atlas-2026-07-17/.memlog.md",
]

def slug(s):
    return "".join(c if c.isalnum() or c == "-" else "-" for c in s.lower()).strip("-")

def rel(p):
    return str(p.relative_to(ROOT))

parts = []
H = []
H.append("# pyforge-atlas — consolidated BMAD specs")
H.append("")
H.append("> **What this is.** Every BMAD spec/planning artifact used to build the")
H.append("> `pyforge-atlas` Kedro migration, concatenated into one file for reference.")
H.append("> Each section preserves its source content verbatim under a heading that names")
H.append("> the original path and tier. This is a *derived archive* — the source files")
H.append("> under `_bmad-output/projects/pyforge-atlas/` and `docs/specs/` remain the")
H.append("> canonical, editable copies.")
H.append(">")
H.append("> **Provenance & cross-session note.** The Tier-2 planning artifacts are")
H.append("> git-tracked, so cross-session committed work is already captured here. Tier-3")
H.append("> story files are gitignored local state: only waves **0 / A / B** exist as")
H.append("> individual story-file specs — waves **C–H** ran through the in-session agent")
H.append("> loop and were never emitted as story files, so their per-story detail lives")
H.append("> only inside **epics.md** (all 32 stories are defined there). Anything authored")
H.append("> in another session and never committed is NOT reachable from this checkout.")
H.append(">")
H.append(f"> Generated: {datetime.date.today().isoformat()} · binding spec version: see the intake spec's frontmatter.")
H.append("")
H.append("---")
H.append("")
H.append("## Table of contents")
H.append("")
# TOC + provenance rows
toc = []
prov = ["| # | Section | Tier | Source path | Bytes |", "|---|---|---|---|---|"]
n = 0
for title, tier, path, _ in SECTIONS:
    n += 1
    exists = path.exists()
    anchor = slug(f"{n}-{title}")
    toc.append(f"{n}. [{title}](#{anchor})" + ("" if exists else " — *(missing locally)*"))
    size = f"{path.stat().st_size:,}" if exists else "—"
    prov.append(f"| {n} | {title} | {tier} | `{rel(path)}` | {size} |")
H.extend(toc)
H.append("")
H.append("### Provenance")
H.append("")
H.extend(prov)
H.append("")
H.append("---")
H.append("")
parts.append("\n".join(H))

# body
n = 0
for title, tier, path, lang in SECTIONS:
    n += 1
    anchor_line = f"## {n}. {title}"
    block = [anchor_line, "", f"> **Tier:** {tier} · **Source:** `{rel(path)}`", ""]
    if not path.exists():
        block.append("*(File not present in this checkout — see the cross-session note above.)*")
        parts.append("\n".join(block))
        parts.append("\n---\n")
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    if lang:
        block.append(f"```{lang}")
        block.append(text.rstrip("\n"))
        block.append("```")
    else:
        # demote nothing; keep verbatim. Content already uses its own heading levels.
        block.append(text.rstrip("\n"))
    parts.append("\n".join(block))
    parts.append("\n---\n")

# appendix index
ap = ["## Appendix — process artifacts (not inlined)", "",
      "PRD/architecture review, validation, rubric, and `.memlog` files — process",
      "evidence rather than specs. Listed here with paths; read them in place.", "",
      "| Artifact | Path | Bytes |", "|---|---|---|"]
for p in APPENDIX:
    size = f"{p.stat().st_size:,}" if p.exists() else "—"
    ap.append(f"| {p.name} | `{rel(p)}` | {size} |")
ap.append("")
ap.append("Also excluded: `forge-data/` (Skill-Forge outputs for the `cf-atlas-legacy` "
          "contextual skill) under the implementation-artifacts dir.")
parts.append("\n".join(ap))

OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"Wrote {OUT}")
print(f"Total bytes: {OUT.stat().st_size:,}")
print(f"Sections: {len(SECTIONS)} · appendix entries: {len(APPENDIX)}")
missing = [rel(p) for _, _, p, _ in SECTIONS if not p.exists()]
print("Missing sections:", missing or "none")
