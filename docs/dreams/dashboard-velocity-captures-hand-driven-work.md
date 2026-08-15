---
title: Dashboard velocity counts every story's real effort, not just bmad-loop-journaled ones
type: dream
owner: marshal
status: dreamt
---

# Dashboard velocity counts every story's real effort, not just bmad-loop-journaled ones

## The Dream

The factory console's velocity chart (`docs/dashboard/generate.py`'s `# ---- delivery
timing / velocity (derived from bmad-loop run journals) ----` section) shows "active
agent-compute per story" — but only for stories that ran through `bmad-loop`, because it is
literally "derived from every loop home's journals" (per-run session logs bmad-loop itself
writes). A story implemented any other way — `bmad-dev-auto` hand-driven outside the loop
(`bmad-quick-dev`, or the assistant orchestrating a sequence of `bmad-dev-auto` calls itself,
as doctor's Epic 8 was on 2026-08-15), a manual `bmad-quick-dev` session, anything that isn't
a bmad-loop run — leaves no journal, so it lands in the same "not measured" bucket as
stories that predate loop instrumentation entirely, even though real effort/duration data
exists for it (git commit timestamps, subagent session durations, or a story's own
`baseline_revision`/`final_revision` spec-file fields).

The chart's own caption is honest about this ("18 of 41 stories measured; the rest predate
loop instrumentation... deliberately absent rather than plotted"), but that caption's
framing — "predates instrumentation" — no longer covers every case in the bucket. A
hand-driven story finished TODAY, with a real git history and real timing available, is
absent from the same reason a story from before the loop existed at all is absent. Those are
different situations with the same symptom.

## What it looks like when real

- Every `done` story contributes SOME timing signal to the console, sourced from whichever
  fidelity is actually available: bmad-loop journal (highest fidelity, current behavior,
  unchanged) > a hand-authored/derived wall-clock duration from the story spec's own
  `baseline_revision`→`final_revision` git range (lower fidelity, but real) > absent only
  when genuinely no timing data exists at all (pre-instrumentation legacy stories with no
  spec file carrying those fields).
- `generate.py` already has the mechanism this needs half-built: its own docstring says
  "Hand-authored `timing`/`velocity` are PRESERVED, never overwritten" — the write path for
  a CURATED (non-derived) entry already exists (this is how Warden's/Atlas's own
  once-computed-then-preserved numbers survive re-runs today). What's missing is a
  CAPTURE step that populates that curated slot for a hand-driven story, not the storage.
- Two candidate capture points, either or both: (a) `bmad-dev-auto`'s own HALT protocol
  gains a lightweight timing stamp (it already writes `baseline_revision`/`final_revision`
  into the spec's frontmatter at exactly the right moments — adding a duration derived from
  those two commits' timestamps is a small, natural extension); (b) `generate.py` itself
  back-fills a wall-clock-only data point for any `done` story with a spec file carrying
  both revision fields but no bmad-loop journal, distinguishing it visually from
  journal-derived "active agent-compute" bars (same distinction the existing "timing strip"
  already makes for legacy stories, per the chart's own caption).

## What is real

Nothing. Confirmed absent 2026-08-15: after doctor's Epic 8 landed (4 stories, hand-driven
via `bmad-dev-auto`, real adversarial review and real landing PRs for every one), the
dashboard's velocity chart shows no bars for 8.1–8.4 — verified by reading
`generate.py`'s own velocity-derivation code, which only walks bmad-loop journals.

## Constraints

- Never fabricate a number for a story with genuinely no data — the existing "deliberately
  absent rather than plotted" discipline for undated legacy stories must survive.
- A wall-clock-derived fallback measures something DIFFERENT from bmad-loop's own
  "active agent-compute, excludes gate-pause wait" — must be visually/textually
  distinguished, not silently blended into the same bar type as if it were equally precise.
- Preserve the existing hand-authored-value-is-never-overwritten guarantee — Warden's and
  Atlas's already-curated numbers must not be touched by whatever capture mechanism lands
  here.

## Non-goals

- Not retrofitting timing for stories with no spec file at all (truly pre-instrumentation,
  no revision fields to derive from) — those stay absent, correctly.
- Not building a NEW orchestration path — this only affects how already-shipped work
  (via `bmad-dev-auto`/`bmad-quick-dev`, whichever route a story actually took) gets
  reflected in the console, not how it gets built.

## Kinships

[[factory-console]] (the console this Dream extends — owner: marshal, realized, narrative
absorbed into [[pyforge-marshal]]) · doctor's Epic 8 (2026-08-15, the concrete case that
surfaced this gap — hand-driven via `bmad-dev-auto`, see the session's own project memory
`project_session_close_2026-08-15_epic8_doctor` for the full worked example).

## Realization log

- **2026-08-15** — Dream captured. Surfaced when the user pointed out doctor's Epic 8
  (hand-driven, no bmad-loop) has no velocity bars on the live dashboard, and asked
  whether this had been captured as backlog before ending the session. It had not — only
  noted in the assistant's own personal session-memory, not as a repo-tracked Dream. This
  file is that capture.
