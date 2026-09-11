---
title: 'The 2 identity contradictions are fixed at their source'
type: 'fix'
created: '2026-09-11'
status: 'done'
baseline_revision: 'a7752e7f91015b81d79a979bfca61a0dc8c8c8bb'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Two authoritative sources in this repo contradict every other source that
describes the same fact. `src/shared/packages/pyforge-doctor/README.md:6` claims Doctor
consolidates warden + cf_atlas signals into "its own exit-code gate" — but
`.claude/skills/pyforge-doctor/skill-brief.yaml`, `CLAUDE.md`'s SKF block, and `AGENTS.md`
all state explicitly that Doctor's findings are "advisory — not a second PR gate," "never a
competing PR verdict." "Gate" is a loaded, specifically-owned term in this repo (Warden
legitimately is one); Doctor's own README borrows it for a station that is everywhere else
defined by NOT being one. Separately, `AGENTS.md:111` assigns Herald "keeping the Dream →
spec handoff portable across agents," but Herald's own Dream
(`docs/dreams/pyforge-herald.md`) explicitly disclaims this responsibility by name, citing a
dated 2026-07-23 ownership review that assigned it to Marshal instead.

**Approach:** Two surgical, single-location edits. `pyforge-doctor/README.md:6` drops the
"gate" framing and states the advisory framing instead, matching `skill-brief.yaml`/
`CLAUDE.md`/`AGENTS.md`'s own wording. `AGENTS.md:111` either names Marshal instead of Herald,
or is reworded to make no ownership claim about who owns the handoff (the story does not
mandate which — whichever reads more naturally in context, as long as it stops contradicting
`docs/dreams/pyforge-herald.md`). Neither file gets a wholesale rewrite; only the contradicting
clause in each changes.

## Boundaries & Constraints

**Always:**
- Touch only the specific contradicting clause in each of the two files — no wholesale
  rewrite of `pyforge-doctor/README.md` or `AGENTS.md`.
- The corrected Doctor framing must match `skill-brief.yaml`/`CLAUDE.md`/`AGENTS.md`'s existing
  "advisory — not a second PR gate" language, not invent new wording.
- The corrected `AGENTS.md` line must agree with `docs/dreams/pyforge-herald.md`'s own
  ownership claim (Marshal owns cross-agent portability; Herald owns the communication face
  only) — read that Dream's `## The Dream` section before editing to confirm the exact
  current framing has not drifted since this story was written.

**Never:**
- Do not touch any other line in either file beyond the two identified contradictions.
- Do not introduce a THIRD framing for either fact — the fix must match what the other
  authoritative sources already say, not invent new language.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Doctor README gate language | `README.md:6` reads "...and its own exit-code gate." | Reworded to the advisory framing, matching `skill-brief.yaml`/`CLAUDE.md`/`AGENTS.md` | n/a — content fix, not code |
| AGENTS.md Herald ownership claim | `AGENTS.md:111` reads "...is **Herald's** job." | Reworded to name Marshal, or reworded to make no ownership claim, matching `docs/dreams/pyforge-herald.md` | n/a — content fix, not code |
| Dream drift check | `docs/dreams/pyforge-herald.md`'s own ownership claim has changed since this story was written | Re-read the live Dream before editing; match its CURRENT wording, not this spec's quoted text | Named in the PR description if the live text differs from what this spec quotes |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/README.md` — line 6, the "gate" framing.
- `AGENTS.md` — line 111, the Herald ownership claim.
- `docs/dreams/pyforge-herald.md` — read-only reference for the correct ownership framing.
- `.claude/skills/pyforge-doctor/skill-brief.yaml`, `CLAUDE.md` — read-only reference for the
  correct Doctor "advisory" framing.

## Tasks & Acceptance

**Execution:**
- `fix` — reword `pyforge-doctor/README.md:6` to drop "gate" language, matching the advisory
  framing used everywhere else.
- `fix` — reword `AGENTS.md:111` to name Marshal (or make no ownership claim), matching
  `docs/dreams/pyforge-herald.md`.

**Acceptance Criteria:**
- Given `pyforge-doctor/README.md` currently claims "its own exit-code gate," when the line is
  reworded to match `skill-brief.yaml`/`CLAUDE.md`/`AGENTS.md`'s "advisory — not a second PR
  gate" framing, then `pyforge-doctor/README.md` no longer uses gate language for itself.
- Given `AGENTS.md` currently assigns Herald "keeping the Dream → spec handoff portable across
  agents," when the line is corrected, then `AGENTS.md`'s cross-agent-portability claim names
  Marshal (or makes no ownership claim at all), matching `docs/dreams/pyforge-herald.md`.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — expected: clean for
  `pyforge-herald` (no new contradiction introduced).
- Manual read-through: `grep -n "gate" src/shared/packages/pyforge-doctor/README.md` shows no
  self-referential gate claim; `grep -n "Herald" AGENTS.md` around the corrected line agrees
  with `docs/dreams/pyforge-herald.md`.

## Auto Run Result

Status: done
Summary: `pyforge-doctor/README.md:5-6` reworded from "its own exit-code gate" to "findings
stay advisory — not a second PR gate," matching `skill-brief.yaml`/`CLAUDE.md`/`AGENTS.md`.
`AGENTS.md:111` reassigned cross-agent portability from Herald to Marshal, matching
`docs/dreams/pyforge-herald.md`.
Files changed:
- `src/shared/packages/pyforge-doctor/README.md`
- `AGENTS.md`
Review: `bmad-build-auto`'s own 4-layer pass — 10 Blind Hunter observations (all
defer/reject, out of scope or AC already met), 0 Edge Case findings, no verification gaps
(doc-only change), diff matches the minimal surgical fix reading. 0 patch findings, no
follow-up review recommended.
Verification: `pixi run --frozen -e local-recipes dreams-hygiene-check` — exit 0. Manual grep
confirmed both corrected lines.
Blocking condition: none
