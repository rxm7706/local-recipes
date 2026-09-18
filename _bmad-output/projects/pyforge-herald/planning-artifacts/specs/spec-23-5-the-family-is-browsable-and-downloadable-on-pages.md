---
title: '23.5: The family is browsable and downloadable on Pages'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
baseline_revision: '36ccbfa9f9d2c1b06a2a5ff7a0c2561a8a10778b'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      No PR-gating CI lane runs docsite/build.py or site-check before merge, and this
      story's own mandated Verification command (pyforge-herald-test) has zero coverage
      of docsite/, so a regression in the family-page code (or the pre-existing
      dossier/gallery/artifact code) can merge to main with every gate green.
    evidence: |-
      Verified 2026-09-18: grepped every `pull_request`-triggered workflow and
      `pr-preflight`'s dependency list in pixi.toml — none reference `docsite` or
      `site-check`. `dashboard.yml`, the only workflow that runs the build, triggers on
      `push: branches: [main]` only. No `docsite/tests/` directory or any test file
      anywhere imports `docsite/build.py`. This is pre-existing for the whole docsite
      pipeline (dossier/gallery/artifact already had zero PR-gating CI and zero unit
      tests before this story) — not introduced by this diff, so it is out of this
      story's scope to fix.
    location: >-
      pixi.toml (pr-preflight, feature.site.tasks.site-check), .github/workflows/dashboard.yml
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** docsite/build.py publishes standalone infographics only — no PPTX, Marp, exec summary, or per-deck page.

**Approach:** One family page per registered deck plus an index. Poster, Infographic Deck, Executive Summary in view; PPTX(s) and Marp as downloads; etag and tree stamps. dashboard.yml remains the only deploy-pages caller.

## Boundaries & Constraints

**Always:**
- Kedro-Viz stays at /kedro-viz/.
- One deploy-pages caller.

**Never:**
- Do not add a second Pages deploy.
- Do not bind a new Pages product.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| site-check | after family pages land | passes | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-7; spec-pyforge-pages CAP-1/CAP-2`.
Surface: docsite/build.py; docsite/templates/**; docsite/content/**; docs/dashboard/**; site-check..
Ledger key: `23-5-the-family-is-browsable-and-downloadable-on-pages`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-5-the-family-is-browsable-and-downloadable-on-pages.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's policy `verify_commands` entry; MRS-GATE-010 binds the dispatch gate to this Success signal, and it is read from the primary tree's tracked spec, so it must be declared here before dispatch, not by the session).

**Manual checks:**
- `site-check` passes after the family pages land; each family page shows the poster, Infographic Deck and Executive Summary in view, offers the PPTX(s) and Marp sources as downloads, and stamps each with its etag and tree; `dashboard.yml` is still the only `deploy-pages` caller and Kedro-Viz is still at `/kedro-viz/`.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 18 findings — high 0, medium 7, low 10, false 1, maybe-false 0
- findings:
  - `[low]` `[patch]` Landing page (`page_index.html.j2`) has cards for Dossier and Infographics but none for the new Decks section, even though `site.yml` gained a `decks` nav entry — verified: `card-grid` only has two `<a class="card">` entries plus the `site.neighbours` loop. Applied: added a third card linking `decks/index.html`, mirroring the Infographics card's shape and reporting `{{ families | length }}`.
  - `[low]` `[patch]` `publish_family_views` injects the family back-bar unconditionally, unlike `publish_infographic` which gates it behind `site_cfg["infographics"].get("inject_backbar", True)` — verified at `docsite/build.py:350-372` (no `inject` param). Currently harmless (`inject_backbar: true` in site.yml) but a real inconsistency if ever flipped. Applied: `publish_family_views` now takes an `inject: bool` param, gated the same as `publish_infographic`; the `build()` call site passes the same computed `inject` value.
  - `[low]` `[reject]` Default `page_description` for a family page always lists "Infographic Deck, Executive Summary, PowerPoint and Marp sources" regardless of what the deck actually has (2 members: Blind Hunter + Edge Case Hunter both flagged this) — verified real at `docsite/build.py:534-537`, but all 10 currently-registered decks have every artifact type (confirmed via `site-check` output), so it manifests for no deck today, and a correct fix requires new conditional branching (more than a direct correction) — rejected per the low-and-non-trivial-fix rule.
  - `[medium]` `[patch]` `check()` validates the top-level `decks/index.html` for size/existence but the per-deck `decks/<slug>/index.html` pages only get an existence check (no "suspiciously small" or unrendered-Jinja-delimiter check, unlike `dossier/index.html`) — verified at `docsite/build.py:612-629`, a truncated/half-rendered family page would pass `--check` silently. Applied: the per-family loop now also checks each `decks/<slug>/index.html` for `<500B` size and for unrendered `{{`/`{%` delimiters.
  - `[low]` `[patch]` `main()`'s console summary collapses a family's status to only `"poster+ID+ES"` or `"poster only"` (2 members: Blind Hunter + Edge Case Hunter both flagged this) — verified at `docsite/build.py:667-672`, a deck with exactly one of Infographic Deck/Executive Summary is mislabeled "poster only". Harmless today (no partial deck exists) but the fix is a direct correction. Applied: the label is now built incrementally (`poster`, `+ID` if present, `+ES` if present, `"poster only"` only when neither is present).
  - `[low]` `[patch]` `page_family_index.html.j2` hardcodes `"../infographics/..."` instead of using the `{{ rel }}` variable already passed into the template (equal to `"../"` here) — verified at the template's `data-preview` attribute; every sibling template uses `{{ rel }}`. Applied: changed to `{{ rel }}infographics/{{ fam.poster.out_name }}`.
  - `[low]` `[patch]` `_artifact_stamp`'s sidecar-stamp branch returns the etag at full length while the fallback branch truncates its digest to 12 chars, so etag display length will differ once real stamp sidecars exist — verified at `docsite/build.py:258-268`. No sidecar exists yet for any deck today (confirmed by the implementation subagent's own report), so this doesn't manifest yet, but the fix is a trivial one-line truncation, so it does not qualify for auto-reject. Applied: the sidecar branch now truncates `etag` to `[:12]` too.
  - `[false]` `[reject]` A future PR for this branch needs the `maintenance` label per this repo's PR gates, and "nothing in the diff... evidences that label has been applied" — refuted: this `bmad-build-auto` run does not open a PR at all, so there is nothing to have labeled yet; this is forward guidance for whoever opens the PR, not a defect in the diff.
  - `[low]` `[reject]` `check()`'s decks-index membership check (`if slug not in decks_index`) is a bare substring match, so a slug appearing elsewhere on the page could false-pass a broken link — verified real at `docsite/build.py:618-619`, but this is the same bare-substring pattern the pre-existing `if item["out_name"] not in gallery` infographics check already uses in this file (established precedent, not a new weaker pattern), the slugs involved are long and distinctive, and a proper fix (href-specific parsing) is more than a direct correction — rejected per the low-and-non-trivial-fix rule.
  - `[medium]` `[patch]` `_listed_files` returns every historically-dated file in a deck's `src/pptx`/`src/marp` directories, not just the current one(s) — verified live: `pyforge-atlas`'s family page downloads list ships all 6 PPTX files (3 dates × 2 product types: `pyforge-atlas-deck-*` and `pyforge-atlas_infographic_deck-*`) and all 11 Marp files, not just the current export, diverging from the intent's "PPTX(s) and Marp as downloads" (plural products, not plural dated history). Applied: `_listed_files` now groups by filename with the trailing `-YYYY-MM-DD` suffix stripped (a new `_DATE_SUFFIX_RE`) and keeps only the newest-dated file per group; verified live, `pyforge-atlas` now lists exactly 2 PPTX / 5 Marp (the current `2026-09-15` exports only).
  - `[medium]` `[defer]` No PR-gating CI lane ever runs `docsite/build.py`/`site-check` before merge, and the story's own mandated Verification command (`pyforge-herald-test`) has zero coverage of `docsite/` (3 members: Verification Gap Reviewer's main finding + Intent Alignment Auditor's same observation + Blind Hunter's "no unit tests" finding) — verified: grepped every `pull_request`-triggered workflow and `pr-preflight`'s dependency list, none reference `docsite`/`site-check`; `dashboard.yml` (the only workflow that runs the build) triggers on `push: branches: [main]` only. This is pre-existing for the whole docsite pipeline (dossier/gallery/artifact already had zero PR-gating CI and zero unit tests before this story), not introduced by this diff — routes to defer, not patch. Recorded in frontmatter `deferred`.
  - `[medium]` `[patch]` `docs/dashboard/`'s `.gitignore` block lists every `OWNED_OUTPUTS` entry individually (`index.html`, `.nojekyll`, `assets/`, `dossier/`, `infographics/`, `artifact/`) but has no `docs/dashboard/decks/` line even though this diff adds `"decks"` to `OWNED_OUTPUTS` (2 members: Verification Gap Reviewer + Intent Alignment Auditor both flagged this) — verified at `.gitignore:966-973`. A local build into `docs/dashboard/` (the same `--out` CI uses) leaves `decks/` untracked-and-not-ignored, unlike every sibling output, risking an accidental `git add` of binary PPTX exports. Applied: added `docs/dashboard/decks/` next to `docs/dashboard/infographics/`.
  - `[low]` `[patch]` `docsite/README.md`'s "Outputs land in `dist/`" table was not updated to list the two new output paths (`decks/index.html`, `decks/<slug>/index.html`) — verified: table stops at `assets/site.css`. Applied: added two rows.
