---
sources:
  - docs/foundry/upstream-todos.yaml
  - scripts/upstream_todos_check.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-67-4-upstream-tickets-for-the-gaps-that-need-one.md
verified: 2026-10-10
---

# How to Track Upstream To-Dos

PyForge records upstream work **in this repository only**. Agents may propose items and write paste-ready drafts; **only the operator** files issues, marks them tracking, resolves them, or retires them (Story 85.8 outward-write denials).

## Read the registry

- **Registry:** `docs/foundry/upstream-todos.yaml` — one `items[]` entry per upstream gap or session finding.
- **Drafts:** `docs/foundry/upstream-drafts/<id>.md` — five sections (`## Title` … `## What resolution unblocks here`) ready to paste into GitHub.

Run the check:

```bash
pixi run -e pyforge-guild upstream-todos-check
```

It also runs under `detectors-ci` as repo-scope detector `upstream_todos_check`.

## File an item (operator)

1. Open the draft for the item id.
2. Create the upstream issue or PR using your account (not an agent session).
3. Tell an agent in chat, for example: `mark sbom-crm-click-cap filed at https://github.com/…/issues/N`.
4. The agent sets `state: filed`, `decided_by: operator`, today's `date`, `issue_url`, and appends the prior state to `history`.

## Track, resolve, retire (operator)

- **Tracking:** operator sets `state: tracking` with a valid `issue_url`. Agents may refresh `observed` with read-only `gh issue view` / `gh pr view` GETs only.
- **Resolved:** operator sets `state: resolved` with `local_follow_up` (`done: …` or a story key) after upstream fixed the problem and local follow-up landed.
- **Retire:** operator sets `state: retired` with a `reason` when the item no longer applies.

## When the check names an uncovered upstream row

`upstream-todos-check` prints a **proposed** YAML stub for any `upstream` row in `docs/foundry/sbom-gaps.md` with no matching `source: sbom-gaps:<id>`. Add that stub to `upstream-todos.yaml`, write the draft file, and land both in the same PR as the new SBOM row.

## SBOM gap list gate (separate from this registry)

The gate keeping `docs/foundry/sbom-gaps.md` aligned with `pixi.toml` is `tests/scripts/test_sbom_gap_derive.py::test_live_document_matches_derivation`, run on every PR by the `scripts-suite` job of `.github/workflows/detectors.yml` and locally by `pr-preflight`'s `pyforge-doctor-scripts-test` leg; run the same derivation by hand with pixi task `sbom-gaps-check`.
