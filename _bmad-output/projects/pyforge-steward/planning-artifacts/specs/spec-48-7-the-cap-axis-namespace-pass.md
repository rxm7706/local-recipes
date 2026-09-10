---
title: "Story 48.7: The CAP-axis namespace pass"
type: story
created: 2026-09-10
baseline_revision: f27553a3de627e410910297ab5b1fe9683d04654
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - scripts/ad_citation_check.py
  - scripts/.ad-citation-baseline.json
  - scripts/pixi_env_matrix.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md
warnings: []
deferred: []
declared_low_risk: false
---

# Story 48.7: The CAP-axis namespace pass

<intent-contract>

## Intent

**Problem:** The 2026-09-08 AD/FR pass (`b8b142db63`) qualified cross-spine AD citations but left ~185 bare `CAP-n` cites in non-canopy satellites — same ambiguity class, now on the capability axis. Six `Canopy canopy:AD-n` double-prefix artifacts and space-form `python-agent-platform CAP-n` / `canopy CAP-n` stragglers remain. Document-tier residue in `stack.md` still reads as blocking feedstock work; `pixi_env_matrix.py` embeds a broken regen command.

**Approach:** Mirror the AD convention on CAP: bare `CAP-n` means Unifying only; satellite chains use `fnd:`, `suite:`, `sld:`, `uc:`, `pap:`, `jira:`, `canopy:` as appropriate. Qualify cites in spine satellite ranges and Epics 9/39/45–47; clean double-prefix and space-form stragglers; extend `ad_citation_check.py` with CAP detection + baseline ratchet; fix `stack.md` historical Absent table, High-Leverage matrix bindings, and floor pins; fix `render_markdown` regen string; record `pyforge.*` import carve-outs in Unifying SPEC Residual (not an absolute ban).

## Boundaries & Constraints

**Always:** Preserve referent — rewrite form only, never renumber. Inside a Spec's own § Capabilities block, bare `CAP-n` stays definitional. `pap:` remains a live prefix (never fold into `canopy:`). Re-stamp CAP baseline only when the known set shrinks.

**Never:** Hand-edit `sprint-status-ledger.yaml`. Do not rename `[feature.python-agent-platform]`. Do not merge Single-Spec text (48.8). Do not fix unrelated bare AD cites unless introduced by this diff.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| QUALIFIED_OK | `suite:CAP-2` in epics.md Epic 46 | Detector passes | N/A |
| BARE_FAIL | bare `CAP-2` in Epic 46 FR/AD line | `ad_citation_check` reports NEW issue | Qualify to `suite:CAP-2` |
| CANOPY_HOME | bare `CAP-11` in Unifying SPEC § Capabilities | Allowed | N/A |
| SPACE_FORM | `python-agent-platform CAP-5` in Epic 10 | Becomes `pap:CAP-5` | N/A |
| DOUBLE_PREFIX | `Canopy canopy:AD-13` | Becomes `canopy:AD-13` | N/A |

</intent-contract>

## Code Map

- `scripts/ad_citation_check.py` — add `_CAP_DEF`, `_CAP_CITE`, `_defined_caps`, CAP scan loop, `.cap-citation-baseline.json` ratchet (parallel AD machinery)
- `scripts/pixi_env_matrix.py:93-94` — broken `--update docs/dreams/...` → `--update --dream docs/dreams/...`
- `.../ARCHITECTURE-SPINE.md:578-896` — foundry satellite; qualify bare CAP cites (`fnd:` for cutover CAP-1..10, `canopy:` for Unifying estate CAPs)
- `.../ARCHITECTURE-SPINE.md:897-1246` — sld satellite → `sld:CAP-n`
- `.../ARCHITECTURE-SPINE.md:1247-1425` — uc satellite → `uc:CAP-n`
- `.../ARCHITECTURE-SPINE.md:1426-1653` — suite satellite → `suite:CAP-n`
- `.../ARCHITECTURE-SPINE.md:1654+` — jira satellite → `jira:CAP-n`
- `epics.md:768-843` — Epic 9 → `sld:CAP-*`
- `epics.md:2303-2347` — Epic 39 → `suite:CAP-*`
- `epics.md:2767-2915` — Epics 45–47 → spec-qualified / `suite:CAP-*`
- `epics.md:856-997` — Epic 10 space-form → `pap:CAP-*`
- `stack.md:16-19,81-98,52-74` — floor pins, historical Absent table, High-Leverage matrix corrections
- `SPEC.md:32` — remove dangling `recipes/cachebox/**` from `surface:`
- `resilience-invariants.md:25,106` — `Canopy AD-7` → `canopy:AD-7`; CAP column bare → `canopy:CAP-n` where Unifying
- Six double-prefix files — `Canopy canopy:AD-n` → `canopy:AD-n`

## Tasks & Acceptance

**Execution:**
- `scripts/ad_citation_check.py` — extend with CAP citation check + `--write-cap-baseline` — regression gate
- `scripts/.cap-citation-baseline.json` — initial baseline after pass
- `scripts/pixi_env_matrix.py` — fix embedded regen command
- `ARCHITECTURE-SPINE.md` — qualify bare CAP cites in non-canopy satellite sections
- `epics.md` — qualify Epics 9, 39, 45–47; fix Epic 10 space-form
- `stack.md` — document-tier residue (Absent historical, matrix, floor)
- `SPEC.md` — remove cachebox glob; append import-rule carve-out note to Residual
- `resilience-invariants.md` — fix L25 AD space-form + CAP column qualification
- Six spec files + `sprint-change-proposal-2026-09-05-ad-1-reopen.md` — remove `Canopy canopy:` double-prefix
- `src/platform/config/*.py`, `langflow_integration/*`, `dbgpt_integration/*` — `pap:CAP-*` in comments

**Acceptance Criteria:**
- Given `python scripts/ad_citation_check.py`, when run from repo root, then exit 0 with no NEW CAP issues
- Given spine satellite sections outside Canopy (L578+), when grepped for `(?<![\w:-])CAP-[0-9]`, then zero matches outside definitional headings
- Given Epic 9/39/45–47 story FR/AD lines, when read, then every CAP cite carries the correct satellite prefix
- Given `stack.md` Absent section, when read, then it is titled/dated historical and cachebox premise removed
- Given `pixi_env_matrix.py` render output, when read, then regen command includes `--dream` flag
- Given six double-prefix files, when grepped for `Canopy canopy:`, then zero matches

## Verification

**Commands:**
- `python scripts/ad_citation_check.py` — expected: exit 0, no NEW CAP or AD issues
- `pixi run -e local-recipes ad-citation-check` — expected: exit 0
- `python scripts/pixi_env_matrix.py --check docs/dreams/pyforge-unifying-strategy.md` — expected: exit 0 or stale only if lock unchanged
- `rg 'Canopy canopy:' _bmad-output docs src/platform` — expected: no matches
- `rg 'python-agent-platform CAP-' _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` — expected: no matches

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 1, false 2, maybe-false 0, reject 1
- findings:
  - `[false]` `[reject]` Fleet-wide bare CAP cites in doctor/marshal/atlas baselined — intentional ratchet; steward satellite pass is complete; cross-station qualification is follow-on work outside 48.7 surface
  - `[false]` `[reject]` CAP baseline of 108 entries looks large — matches measured cross-project cites pre-pass; zero NEW issues after baseline stamp
  - `[low]` `[reject]` Dream pixi-env-matrix block still stale vs lock — lock unchanged this run; regen command fix self-heals on next lock bump
  - `[false]` `[reject]` Foundry binds mixing `fnd:` and `canopy:` — verified against cutover memlog: CAP-1..10 are fnd namespace; estate CAP refs correctly use `canopy:`

## Design Notes

Foundry satellite CAP-1..10 are a different namespace from Unifying CAP-1..19 — qualification disambiguates. Suite lifecycle CAP-1..8 bind in suite satellite Binds lines. The detector treats qualified definitions (`#### fnd:CAP-1`) as separate namespace from bare definitions, mirroring AD fold semantics.

## Auto Run Result

**2026-09-10 — Story 48.7 landed in dispatch worktree.**

- Extended `scripts/ad_citation_check.py` with `_CAP_DEF`, `_CAP_CITE`, `_defined_caps()`, CAP scan loop, and `--write-cap-baseline`; initial baseline at `scripts/.cap-citation-baseline.json` (108 fleet-wide cross-project cites baselined; zero steward satellite bare CAP remaining).
- Qualified ~139 bare `CAP-n` in ARCHITECTURE-SPINE.md satellites (`fnd:`, `sld:`, `uc:`, `suite:`, `jira:`); foundry `canopy:CAP-13` preserved for unifying flag-tree refs.
- Epics 9/39/45–47 FR/AD lines qualified (`sld:`, `suite:`, `pap:`); Epic 10 space-form → `pap:CAP-*`.
- Document tier: `stack.md` Absent → historical (shipped `ed41099205`), floor pins updated, High-Leverage matrix station fixes, cachebox row removed; `SPEC.md` dropped `recipes/cachebox/**`, Residual import carve-out added; `resilience-invariants.md` AD/CAP column fixes.
- Six double-prefix files + `deferred-work-ledger.md` → `canopy:AD-n`; `src/platform/**` comments → `pap:CAP-*`; `pixi_env_matrix.py` regen string fixed.

**Verification (all pass):**
- `python scripts/ad_citation_check.py` → exit 0
- `pixi run -e local-recipes ad-citation-check` → exit 0
- `python scripts/pixi_env_matrix.py --check --dream docs/dreams/pyforge-unifying-strategy.md` → stale (lock unchanged; expected)
- `rg 'Canopy canopy:' _bmad-output docs src/platform` (excl. spec-48-7 doc) → no matches
- `rg 'python-agent-platform CAP-' epics.md` → no matches
- Spine satellites L578+ bare `(?<![\w:-])CAP-[0-9]` → zero matches
