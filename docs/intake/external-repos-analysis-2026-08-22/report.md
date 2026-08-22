# Seven-repo external analysis — millsks + OpenTeams-WFT-CDO (2026-08-22)

Research record (agent-produced, operator-commissioned) grounding five dream
seeds and a set of folds. Full per-repo detail lives in the session record;
this file carries the durable verdicts, the fold list, and the constraints.

## Headline findings

1. **OpenTeams-WFT-CDO is a sibling PyForge instantiation** (the Wells Fargo
   Python-modernization engagement): its `mgmt-wf-python-modernization/docs/dreams/`
   uses THIS repo's Dream-first convention verbatim (same frontmatter, same
   station vocabulary — "the PyForge station accountable"), 13 of its 15
   dreams have local counterparts (8 byte-identical filenames), and the two
   sets are drifting independently with no sync mechanism and diverging
   station ownership (their deck work = scribe; ours = herald).
2. **prf → pypi-to-conda-forge → auto-recipe is one campaign pipeline**
   (score candidates → tracking-issue fleet → staged-recipes v1 draft PRs
   with an LLM CI-fix loop); its intelligence layer is a strict subset of
   atlas+CFE, but it carries mechanisms the fleet lacks (below).
3. **parselmouth is now triple-validated** (FABRIC production use; the org's
   `python-supply-lens` — their only `specified` dream; our own deferred
   memory item) — the atlas evaluation is un-deferred as of this landing.

## Verdicts

| Repo | License | Verdict |
|---|---|---|
| millsks/django-15-factor-base | MIT | ADOPT-AS-DREAM (steward): OIDC-delegated auth, structlog+OTel, startup refusals, policy-as-tests, pixi-sourced deps for src/platform — reference implementation, not a dependency |
| millsks/devinfra | MIT | FOLD into the same steward effort: 13-service compose substrate (Keycloak realm-as-code, LGTM stack, smoke-test.sh, Redis noeviction rationale) |
| millsks/django-python-generate-sbom (FABRIC) | Apache-2.0 | SPLIT: parselmouth strategy + 13×6 manifest corpus FOLD into atlas/warden; the multi-tenant web face ADOPT-AS-DREAM (warden); `_phase_guard` derived-progress pattern noted for atlas Kedro phases. Regenerate parselmouth snapshots from upstream (BSD-3-Clause), never copy theirs |
| OpenTeams prf | none (private) | FOLD patterns only (atlas admission verdict; marker-delimited + ETag-anti-clobber issue sync noted as optional atlas seed) |
| OpenTeams mgmt-wf docs/dreams | none (private, "sanitized") | ADOPT-AS-DREAM ×1 (multi-repo workspaces — the only substantive capability gap in their 15); content-merges for deck trio / bootstrap / bmad-workspace-integration / supply-lens into named local chains; sibling-drift itself becomes a small doctor seed |
| OpenTeams pypi-to-conda-forge | none (private) | FOLD three heuristics into atlas upstream-discovery: all-main-builds-broken version detection, does-the-feedstock-build-from-PyPI-source verification, DoD auto-check from live metadata |
| OpenTeams auto-recipe | none (private) | ADOPT-AS-DREAM (mason): the spec-generated failure catalog with lint-verified `enforced_by` pointers; FOLD Decided/Ambiguous typed uncertainty + the repodata 39-minute-window satisfiability gate + the negative regression corpus into CFE/mason; attempt-economy CI triage into feedstock-failure-remediation |

## The fold list (owning chain picks up at its next story/spec pass)

- **atlas**: parselmouth mapping (snapshot + weekly overlay + curated
  overrides; retires four-spellings) — UN-DEFERRED; p2cf's three heuristics;
  FABRIC `_phase_guard` pattern for Kedro phases; supply-lens specifics →
  `artifactory-download-intelligence` dream.
- **CFE/mason**: Decided/Ambiguous contract; repodata-not-API satisfiability
  (CDN max-age=1200; measured 39-min api-vs-solver window); negative
  regression corpus (generator output that must STAY rejected);
  check_license_semantics-class verify ideas.
- **steward**: attempt-economy triage rules → feedstock-failure-remediation;
  devinfra substrate + their developer-machine-bootstrap command surface →
  the bootstrap dream; bmad-workspace-integration mechanics →
  `bmad-switch-scope-enforcement`.
- **herald**: deck trio deltas (spec.json contract + slide cloning; Pillow
  real-font autofit; deterministic pre-render gates) → pptx-deck-generation
  / pptx-custom-shapes / deck-visual-qa dreams.
- **warden**: FABRIC's 13-archetype × 6-format manifest corpus as
  scan-project/warden fixtures; org's package-inventory-eligibility
  SourceContract/purl shape → the same-name local dream.

## Constraints

- MIT (millsks ×2): copy freely, keep notices. Apache-2.0 (FABRIC): keep
  NOTICE, state changes. **All four OpenTeams repos: NO license, private —
  patterns re-implementable, verbatim code/spec-text/YAML/dream-prose needs
  OpenTeams permission before landing in this repo.**

## Out-of-scope flags

- millsks repos vendor BMAD skills absent locally (`bmad-agent-builder`,
  `bmad-tea` module wiring — the latter is steward 15.3's TEA anyway).
- mgmt-wf's `skills/` (cve-triage, cve-resolve, sync-cvss,
  conda-forge-pr-sync) — warden/doctor interest, not yet analyzed.
- The org pipeline's issue-title handoff is unwired; if collaboration is on
  the table, atlas+CFE could supply the intelligence layer both of their
  weaker halves reimplement.
