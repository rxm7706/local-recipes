---
title: The CFE failure catalog is generated from the skill spec, every row lint-verified against its enforcing check
type: dream
owner: mason
status: realized    # 2026-09-09 — catalog + generator + freshness test + detector all live and green
---

# Machine-checked recipe knowledge

## The Dream

The conda-forge-expert skill's largest asset — 110+ numbered gotchas and the
Build Failure Protocol — is prose. Nothing links a gotcha to the check that
enforces it, so knowledge and enforcement drift silently. The dream: a
failure catalog GENERATED from the skill's own text, one row per failure
class, each carrying greppable symptom signatures and an `enforced_by:`
pointer lint-resolved against the real check surface — with
`enforced_by: null` an explicit, machine-readable automation backlog, and
catalog↔spec drift failing CI.

## Grounding

Proven in the wild by OpenTeams auto-recipe (2026-08-22 seven-repo analysis,
`docs/intake/external-repos-analysis-2026-08-22/`): 45-row
`failure-catalog.yaml` generated from its 980-line spec, lint-resolved
against `verify --list-checks`, "when the two disagree, the spec wins and
the code is wrong." That repo is unlicensed/private — the PATTERN is
adopted; no text or YAML is copied. Locally the fit is exact: the G-corpus
lives in SKILL.md, the check surface in the CFE verify/test machinery, and
the bmad-drift-check philosophy (detector + reconciler + baseline) is the
same shape one level up.

## What it looks like when real

`catalog.yaml` derives from SKILL.md's gotchas; every row names symptom
tokens + its enforcing check (or null); a lint resolves each pointer against
the live check registry; CI reds on drift either way; the null-rows report
IS the prioritized backlog for new checks.

## Constraints / Non-goals

Doctor supplies the drift-lint surface (detector convention), mason owns the
catalog + generation; no verbatim import from auto-recipe (no license);
not a rewrite of the G-corpus — the prose stays authoritative, the catalog
derives. Rule 1/2 apply (CFE surface).

## Kinships

CFE SKILL.md G-corpus · bmad-drift-check (the detector philosophy) ·
`spec-conda-forge-expert-rebuild` (mason's CFE campaign) · the intake report.

## Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-machine-checked-recipe-knowledge` derived under pyforge-mason and decomposed into the
  station backlog the same day (`a20192dd84`). Spec status `ready`.
- **2026-09-09** — **Realized, and exercised** (operator ruling,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.2). `config/failure-catalog.yaml` (117 rows) derives from `SKILL.md`'s gotcha corpus via
  `scripts/failure_catalog_generator.py`, is guarded for freshness by
  `tests/meta/test_failure_catalog_freshness.py` (green), and is independently re-resolved by
  `scripts/failure_catalog_check.py` (`DETECTOR = {"scope": "repo"}` at `:41`, auto-discovered by
  `scripts/detectors.py`) — `pixi run -e local-recipes failure-catalog-check` reports **clean**.
  The Spec flips `ready → shipped` and finally declares its own detector in `surface:`. The
  null-rows backlog is real and large: **115 of 117 rows carry `enforced_by: null` — coverage
  1.7 %**. That number is *emitted on every run* and nobody watches it; raising it is the
  backlog's job, not this Dream's — the Dream's contract was that the number exist and that
  drift be impossible to land silently, and both hold. The Dream's own open question (catalog
  home: `config/` vs `data/`) is settled exactly as it predicted — it landed in `config/`,
  because the artifact is derived-and-tracked.
