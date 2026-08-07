---
name: "bmad-runs-cfe-retro"
description: "Always-on rule — at closeout of any BMAD-driven conda-forge effort, run bmad-retrospective focused on conda-forge-exper…"
metadata:
  type: feedback
---

When a BMAD effort that did conda-forge work reaches closeout (final story complete; PR merged or final review-comment resolved; or the user marks the effort done), the agent **must** run a retrospective focused on the `conda-forge-expert` skill itself.

The retro process:

1. Invoke `bmad-retrospective` (or follow its protocol manually).
2. Review session logs, build failures, recipe diffs, and reviewer comments. Categorize findings as:
 - **Corrections** — skill guidance that was wrong/stale/misleading.
 - **Refinements** — guidance that worked but was harder to apply than necessary.
 - **Additions** — new patterns, constraints, gotchas, or build-failure recipes.
3. Land findings as edits to `.claude/skills/conda-forge-expert/SKILL.md`, `reference/*.md`, `guides/*.md`, and a new `CHANGELOG.md` version entry.
4. Bump skill version per semver (PATCH/MINOR/MAJOR).
5. Cross-skill findings save to auto-memory; skill-internal findings stay in the skill files.

If no novel findings (rare), still produce a CHANGELOG entry stating "no skill changes; verified existing guidance held for: <effort summary>".

**Why:** Every conda-forge effort surfaces edge cases the next effort will hit (e.g., the cocoindex effort surfaced four authoring gotchas now in SKILL.md as G1–G4; the DB-GPT effort already surfaced the itkwasm-vendored-blob precedent). Without a forced retro at closeout, those learnings dissipate and the next effort rediscovers them. The skill is a living artifact, and BMAD-driven efforts are its primary refinement input.

**How to apply:** An effort is not "done" until the retro lands. CLAUDE.md "BMAD ↔ conda-forge-expert integration" § Rule 2 is the canonical durable form of this rule; this memory is the cross-session backup. The retro runs even on smooth efforts — verifying existing guidance held is itself a useful CHANGELOG entry.
