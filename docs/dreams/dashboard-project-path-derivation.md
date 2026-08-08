---
title: The dashboard assumes slug == project directory — it isn't, and won't stay
type: dream
owner: marshal
status: archived
---

# The dashboard assumes slug == project directory — it isn't, and won't stay

> **Consolidated into [[pyforge-marshal]] on 2026-08-08** (§ *Eight more, consolidated
> here*). This file is archived in place: its **Spec stays live and remains the
> contract** — archiving the Dream tier never retires the chain below it. Kept, not
> deleted, so the reasoning that produced the Spec is still readable.

## The Dream

`docs/dashboard/generate.py` and `index.html` build almost every link and
`have`/`gaps` detection by string-gluing a roster slug straight onto
`_bmad-output/projects/<slug>/planning-artifacts/...`. That held while every
chain's slug matched a live project directory 1:1. It stopped holding the
moment stations started absorbing satellite chains and dissolving outright:
`presenton-pixi-image`/`wasm-analytics-stack`/`unity-data-stack` moved into a
Smith's tree without a project dir of their own, `pyforge-genesis` was
retired to `docs/governance/` with none left at all, and `genesis-installer`
writes its epics inside `pyforge-marshal`. Each of these produced the same
bug shape twice already (found 2026-08-02): a naive `have` check reads
"nothing landed" for real, merged work, and the slug's link 404s.

Both known occurrences were just patched in place — `IMPL_CAMPAIGN`'s
`epics_path` field for the build-campaign section, `CAMPAIGN_PROJECT_OVERRIDE`
+ `planning_project` for the planning-campaign section — each with its own
override dict and its own JS link-building special case. That is a fix per
occurrence, not a fix of the pattern: the next dissolution or absorption adds
a third override dict somewhere else in `generate.py`, and a third dead-link
special case somewhere else in `index.html`.

This Dream is not urgent — both current instances are fixed and verified.
It exists so the *next* absorption doesn't rediscover the same bug shape a
third time. Someday: one small derivation helper (`slug -> real project dir,
real epics/PRD/architecture path`) that every roster-driven `have`/link
computation calls, fed by a single override table instead of one per call
site — so a future dissolution is a one-line addition, not a hunt through
`generate.py` and `index.html` for every place that assumed identity.

## What it looks like when real

- One function (Python side) maps a roster slug to its real project
  directory, consulted by every `have`/`gaps` computation in
  `generate.py` — not two separate override dicts (`CAMPAIGN_PROJECT_OVERRIDE`
  today, plus `IMPL_CAMPAIGN`'s per-entry `epics_path`) with duplicated
  reasoning in their comments.
- The generated `data.js` carries enough of that resolution (a real project
  slug, or an explicit "no project dir" marker) that `index.html`'s JS never
  re-derives or guesses a path — today it does, twice, independently.
- Adding a newly-absorbed or newly-dissolved slug to the dashboard is edits
  in exactly one place, and the existing detectors
  (`scripts/dashboard_drift_check.py`, `bmad-drift-check`) would catch a
  slug missing from that table before it ships a dead link.
- `pyforge-genesis`'s redirect to `docs/governance/` — currently a literal
  `r.slug === "pyforge-genesis"` string check inlined in `index.html` — is
  data-driven the same way as every other override, not a special case in
  the rendering code.

## Realization log

- **2026-08-02** — Captured while fixing the second live instance of this
  bug (the planning-campaign section's `CAMPAIGN_ROSTER` link-building,
  alongside the already-fixed build-campaign `IMPL_CAMPAIGN` section) after
  the user reported dissolved/absorbed satellite slugs
  (`presenton-pixi-image`, `wasm-analytics-stack`, `unity-data-stack`,
  `pyforge-genesis`) missing from the dashboard entirely — root cause was the
  same "slug == project dir" assumption in two independent code paths. User
  explicitly deferred the general fix ("seed a dream for later") while both
  concrete occurrences were patched in place same-session. Not yet specified
  or scheduled.
