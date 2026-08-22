---
title: The CFE failure catalog is generated from the skill spec, every row lint-verified against its enforcing check
type: dream
owner: mason
status: dreamt
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
