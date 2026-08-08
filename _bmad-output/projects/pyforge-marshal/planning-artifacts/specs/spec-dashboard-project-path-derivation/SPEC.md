---
id: SPEC-dashboard-project-path-derivation
spec: dashboard-project-path-derivation
status: draft
owner-dream: docs/dreams/dashboard-project-path-derivation.md
surface:
  - docs/dashboard/generate.py
  - docs/dashboard/index.html
sources:
  - ../../../../../docs/dreams/dashboard-project-path-derivation.md
open_questions:
  - "Discovery basis in CI: sprint-status.yaml is Tier-3 gitignored, so a scan of implementation-artifacts finds nothing under a CI checkout — does the derived key set come from tracked planning-artifacts/epics.md presence (as scan_projects already does), with the sprint-status path derived per key, or from a small tracked manifest?"
  - "Does the regen line's _DERIVE_EXCLUDE special (renders its own Spec's 14 stories, not local-recipes/epics.md's 239) become a field on the same override table, or stay a separate mechanism?"
  - "Does _discover_loop_homes()'s independent slug normalization (removeprefix pyforge-, loop-home prefixes) unify onto the same resolver, or stay separate because loop homes live outside the repo?"
---

> **Canonical contract.** This SPEC is the complete contract for the work. The Dream in
> frontmatter is its origin; the code facts below were verified against
> `docs/dashboard/generate.py` on 2026-08-08.

# The dashboard derives project paths — slug ≠ directory stops being a bug factory

## Why

`docs/dashboard/generate.py` string-glues slugs onto `_bmad-output/projects/<slug>/...` in
several independent places, each with its own patch for the slug≠directory cases:

- `PROJECT_SOURCES` (line ~45) — a hardcoded dashboard-key → `sprint-status.yaml` path dict,
  with its own `TODO: Replace hardcoded PROJECT_SOURCES with dynamic discovery` comment. A
  new station is invisible until hand-added; a consolidated project (deckcraft → herald)
  leaves a stale entry. Its **keys** are also reused as the attribution vocabulary for
  hand-landed story subjects in `snapshot_running()` (~line 2526).
- `_KEY_SLUG_OVERRIDE = {"regen": "local-recipes"}` — one divergence, encoded once, but
  consulted at three separate call sites (~166, ~266, ~562), each re-deriving
  `pyforge-<key>` on its own.
- `CAMPAIGN_PROJECT_OVERRIDE` (~861) — absorbed satellites (`presenton-pixi-image` →
  pyforge-mason, `wasm-analytics-stack`/`unity-data-stack` → pyforge-atlas) for the
  planning-campaign `have`/link computation.
- `IMPL_CAMPAIGN`'s per-entry `epics_path` (~904) — the same absorption knowledge again,
  entry-by-entry, for the build-campaign section.
- `index.html` re-derives paths in JS twice, including a literal
  `r.slug === "pyforge-genesis"` redirect special case.

Both known live bugs (found 2026-08-02: real merged work reading "nothing landed", dead
links) came from exactly this "slug == project dir" assumption, and were patched per
occurrence. The next absorption or dissolution adds override dict number five. This Spec is
the pattern fix the Dream deferred.

## Capabilities

- **CAP-1 — one resolver, one override table.** *Intent:* a single Python-side function maps
  a dashboard/roster slug to its resolution — real project directory, planning-artifacts
  paths (epics/PRD/architecture), sprint-status.yaml path, or an explicit
  **no-project-dir** marker — fed by one data table that subsumes `_KEY_SLUG_OVERRIDE`,
  `CAMPAIGN_PROJECT_OVERRIDE`, and `IMPL_CAMPAIGN`'s `epics_path` entries. *Success:* those
  three override surfaces are gone as independent dicts; a future dissolution or absorption
  is a one-line addition to the table.
- **CAP-2 — `PROJECT_SOURCES` is derived, not declared.** *Intent:* the project→
  sprint-status.yaml mapping is discovered from `_bmad-output/projects/*/` structure through
  the CAP-1 resolver instead of the hardcoded dict, so a new station appears without an edit
  and a slug/directory divergence can't silently go unread. *Success:* the `TODO` at
  generate.py:42 is closed; a freshly-added project with the standard layout is picked up by
  `apply_sprint_status()` with zero generate.py edits; `snapshot_running()`'s hand-landed
  attribution vocabulary derives from the same source.
- **CAP-3 — resolution ships in `data.js`; the JS never re-derives.** *Intent:* the
  generated data carries the resolved real project slug (or the explicit no-project marker)
  so `index.html` builds links from data, never by gluing paths itself. *Success:* the
  `r.slug === "pyforge-genesis"` inline redirect check is replaced by data the resolver
  emitted; no path-construction logic remains duplicated between Python and JS.
- **CAP-4 — an unresolvable slug fails loud.** *Intent:* the existing detectors
  (`scripts/dashboard_drift_check.py`, coverage warnings in generate.py) catch a slug
  missing from the table — or a project directory no resolver output covers — before a dead
  link or a false "nothing landed" ships. *Success:* deleting a project dir, or adding a
  roster slug with no resolution, produces a warning/failure on the next generate or
  drift-check run, not a silently wrong board.

## Constraints

- **Always:** the `regen` → `local-recipes` divergence (a dashboard key whose directory does
  not follow `pyforge-<key>`) is table data, exercised by tests — it is the live proof the
  resolver handles slug≠directory.
- **Always:** the pyforge-genesis edge stays semantically intact: dissolved outright to
  `docs/governance/` (not absorbed into a Smith), so `have: all False` remains honest for it
  and only its *link* redirects — the resolver must express "no project dir, redirect here"
  as data, not force-fit it into the absorbed-satellite shape.
- **Always:** absorbed satellites resolve to the owning Smith's tree including non-default
  artifact names (`epics-presenton-pixi-image.md`, `epics-genesis-installer.md` inside
  pyforge-marshal) — resolution is per-artifact-path, not just per-directory.
- **Never:** discovery may not depend on gitignored Tier-3 files *existing* to know the
  project set — `--source git` runs in CI against a checkout where no `sprint-status.yaml`
  exists, and attribution (CAP-2's key set) must still work there.
- **Never:** dashboard content or semantics change — this is a derivation refactor; the
  rendered board for the current fleet is byte-identical modulo the fixed genesis redirect
  plumbing.

## Non-goals

- **Fixing the `GUILD_DREAMS` duplication.** The tuple is deliberately mirrored in
  `scripts/bmad_drift_check.py:620` and `docs/dashboard/generate.py:640` (flagged in
  `docs/governance/spec-pyforge-genesis/SPEC.md`'s own Constraints). Related debt, same
  smell, different surface — not absorbed here.
- **Fixing `station_order` / `station_info` hardcoding in `scan_command_center`
  (generate.py ~1855).** Fleet-membership hardcoding, adjacent to but distinct from
  path derivation; a separate item.
- **A full audit of every hardcoded fleet list in the repo.** This Spec's surface is the
  slug→path derivation bug specifically.

## Success signal

Adding a hypothetical dissolved/absorbed slug to the override table — and nothing else —
yields correct `have` detection, a working link, and correct sprint-status reads across every
dashboard section on the next generate; the `TODO` at generate.py:42 is gone; and grepping
generate.py + index.html finds exactly one place that turns a slug into a filesystem path.
