---
title: 'Every in-place-edited installer-owned file is governed by a marshal spec surface'
type: 'chore'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      No sweep audits already-materialized sprint-status.yaml files elsewhere in the
      fleet for latent pre-existing wrap corruption from before this fix.
    evidence: |-
      Real but out of this story's declared Surface (governance of the 7 files + the
      factory fix only, per the AC). A fleet-wide audit for latent corruption is a
      distinct, larger task -- the one known instance (Story 22.11, 2026-08-31) was
      already hand-repaired at the time.
    location: >-
      .claude/skills/bmad-sprint-planning/scripts/sprint_plan.py
    severity: low
baseline_revision: 'a35c8218566ff2a0c37e72380de7f42f0d70fe57'
---

<intent-contract>

## Intent

**Problem:** Of the seven installer-owned skill files marshal edits in place (four
`.claude/skills/bmad-build-auto/*.md` + three `.claude/skills/bmad-sprint-planning/*`), only
four sit in any marshal spec's `surface:` list today (step-01, step-04, spec-template under
`spec-marshal-single-story-dispatch`; compile-epic-context under `spec-marshal-token-economy`).
The three `bmad-sprint-planning` files fall back to the blanket `.claude/**` allowlist entry,
which never drift-checks them — an edit with no memlog line passes silently. Separately,
`sprint_plan.py`'s `_make_yaml()` dumps at ruamel's default `width=80`, so a `key: value` line
past 80 columns (a long story slug, e.g. this very story's own ledger key) gets folded onto an
indented continuation line that `fleet_scan.parse_sprint_status`'s line-based reader cannot see
— the entry reads as absent. This exact defect bit once already (2026-08-31, Story 22.11,
fixed by hand-reformatting the corrupted file, not by fixing the root cause).

**Approach:** Add the three `bmad-sprint-planning` files to `spec-marshal-single-story-dispatch`'s
`surface:` list (chosen as the ledger-owning spec: its CAP-4 triggers `sprint-ledger-sync` on
landing, its own memlog already narrates the 2026-08-31 incident and explicitly flags this gap),
append memlog entries recording the decision, re-stamp the baseline scoped to that spec, and fix
`_make_yaml()` to set a wide `yaml.width` so the wrap can never recur — with a regression test.

## Boundaries & Constraints

**Always:** Widen exactly the two named specs (`spec-marshal-single-story-dispatch`,
`spec-marshal-token-economy`) — the latter already covers `compile-epic-context.md` and needs
no new entries. Any surface-list change is paired with a `.memlog.md` append (never a silent
frontmatter edit). The width fix is a single-attribute change in `_make_yaml()`, applied
everywhere that factory is used (load, dump, verify) — no second yaml-construction path.

**Never:** Do not touch `spec-sprint-status-auto-promote/SPEC.md` or any other spec's surface
(out of this story's declared Surface). Do not open an upstream PR — record the candidacy only.
Do not change any status *values* while reformatting — this is a coverage + emitter-width fix,
not a ledger content edit. Do not edit `generate-tracking.md`'s content — it only needs surface
coverage, not a behavior change.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Long key, wide dump | `sprint_plan.py generate` mints a ~100-char story key | `key: status` stays on one line in `sprint-status.yaml` | n/a |
| Promoter reads it | The wide-dumped file is fed to `fleet_scan.parse_sprint_status` | The long key's status is present and correct | n/a (this is the regression the fix closes) |
| Planted drift | A future edit lands on any of the seven files with no memlog append | `spec-surface-check` / `pyforge.doctor.sources spec-surface` reports `drift` for the owning spec | Loud FAIL, never silent |

</intent-contract>

## Code Map

- `.claude/skills/bmad-sprint-planning/scripts/sprint_plan.py` -- `_make_yaml()` (~line 277)
  constructs the single ruamel.yaml.YAML() factory used by `_load_existing`, the verify-dump at
  write time (~line 520), and the top-level `main()` yaml instance (~line 676); `_dump_bytes()`
  (~line 391) calls `yaml.dump(doc, buf)`. Reproduced the bug live: a story key >~70 chars wraps
  the `key:` onto its own line with the value indented on the next line.
- `.claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py` -- existing pattern at
  `test_long_title_is_not_truncated_on_first_mint` (line 215) shows how to mint a long-title
  fixture through `run_generate`; add a new test alongside it that also round-trips through
  `fleet_scan.parse_sprint_status`.
- `scripts/fleet_scan.py` -- `parse_sprint_status()` (line 301) and `_ENTRY` regex (line 97, requires
  the full `  key: value` pair on ONE line) are the line-based reader the AC names; imported into
  the test via the same `importlib.util.spec_from_file_location` pattern already used by
  `.claude/skills/conda-forge-expert/tests/meta/test_dashboard_resolve_project.py`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md`
  -- `surface:` frontmatter list (currently 8 entries incl. 3 `bmad-build-auto` files); append the
  3 `bmad-sprint-planning` paths.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/.memlog.md`
  -- tail already narrates the 2026-08-31 promote-parser incident and the 2026-09-06
  "surface widening requested... sprint-planning trio... needs a marshal ledger-owning spec
  surface" direction (unresolved). Append the closing decision + the width-fix event.
- `scripts/spec_surface_check.py` -- `--write-baseline --spec pyforge-marshal/spec-marshal-single-story-dispatch`
  is the scoped-stamp invocation (mutation-only residual; plain `python`, not pixi).
- `scripts/spec_surface_allowlist.txt` line 3 (`.claude/** `) -- confirms why the trio currently
  reads `ok`/allowlisted rather than `uncovered`: allowlist coverage suppresses the ungoverned
  FAIL but never enables drift-checking. No edit needed here.

## Tasks & Acceptance

**Execution:**
- `.claude/skills/bmad-sprint-planning/scripts/sprint_plan.py` -- set `yaml.width` to a wide
  value in `_make_yaml()` -- prevents ruamel from folding long `key: value` lines
- `.claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py` -- import
  `scripts/fleet_scan.py` via `importlib.util.spec_from_file_location`; add a regression test
  that generates a ~100-char story key and re-reads it through `parse_sprint_status`
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md`
  -- add the 3 `bmad-sprint-planning` files to `surface:`
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/.memlog.md`
  -- append decision + event entries closing the 2026-09-06 direction, recording the upstream-PR
  candidacy (not opened) for the width fix
- `scripts/.spec-surface-baseline.json` -- scoped `--write-baseline --spec
  pyforge-marshal/spec-marshal-single-story-dispatch` after the surface + memlog land

**Acceptance Criteria:**
- Given only two of the seven files were governed at the 6.12 apply, when the owning marshal
  spec (`spec-marshal-single-story-dispatch`) claims all seven across the two specs' `surface:`
  lists, then `spec-surface-check` / `python -m pyforge.doctor.sources spec-surface` reports `ok`
  with zero `uncovered` entries, and steward's pre-flight (Story 47.1, run separately) will find
  each of the seven under a spec surface
- Given `sprint_plan.py`'s old `_make_yaml()` (default width 80), when a story key produces a
  `key: value` line past 80 columns, then the fix (`yaml.width` set wide) keeps it on one line,
  and a regression test proves a 100-char key round-trips through `fleet_scan.parse_sprint_status`
  with its status intact
- Given the width fix is an in-place edit to an installer-owned skill file, when the story
  closes out, then the upstream-PR candidacy is recorded in the spec's memlog, not opened as an
  actual PR

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- verdicts: 13 findings — high 4, medium 1, low 4, false 4, maybe-false 0
- findings:
  - `[high]` `[patch]` (blind-hunter) `_make_yaml()`'s `yaml.width = 4096` raises the fold threshold but doesn't eliminate it — a sufficiently long key still wraps — evidence: reproduced live; grouped with the two findings below (same root cause).
  - `[false]` `[reject]` (blind-hunter) new regression test only covers the fresh-generate path, not `_load_existing()`-then-redump — evidence: reproduced the merge-then-redump path directly (fresh generate, then regenerate against the existing file with the same long key) — output stayed on one line both times; the fix lives in the single shared `_make_yaml()` factory called fresh on every path, so there is no separate code path to miss.
  - `[false]` `[reject]` (blind-hunter) `_load_fleet_scan()`'s import of `fleet_scan.py` triggers its module-level `PROJECT_SOURCES` side effect, coupling the unit test to every project's board resolution — evidence: this is the identical `importlib.util.spec_from_file_location` pattern `.claude/skills/conda-forge-expert/tests/meta/test_dashboard_resolve_project.py` already uses against the same module in this repo; `fleet_scan._discovered_epics_files()`'s own docstring documents this as the "CI-safe discovery basis" (glob + `is_dir`, no network); the new test already ran and passed via `uv run` from the repo root.
  - `[low]` `[patch]` (blind-hunter) new memlog decision sentence ("All seven ... now sit under a marshal spec surface") reads ambiguously in isolation — grouped with the intent-alignment D1 finding below (same root cause: the two-spec split isn't self-documenting in both places).
  - `[false]` `[reject]` (blind-hunter) `SPEC.md`'s `updated:` frontmatter left at "2026-09-02" despite this diff widening `surface:` on 2026-09-06 — evidence: the file's own prior history refutes this as a bug — the 2026-09-06 steward-driven surface widening (`spec-template.md`, `compile-epic-context.md`, both still visible earlier in the same memlog) also did not bump `updated:` from "2026-09-02"; the field tracks capability/contract changes (its own inline comment: "CAP-11 added"), not surface-list housekeeping, and this story follows that established convention.
  - `[low]` `[defer]` (blind-hunter) nothing audits already-materialized `sprint-status.yaml` files elsewhere in the fleet for latent pre-existing wrap corruption — evidence: real but out of this story's declared Surface (governance + the factory fix only); a fleet-wide audit is a distinct, larger task. `severity: low`.
  - `[high]` `[patch]` (edge-case-hunter) a story key ≥128 chars forces ruamel's explicit `? key` / `: value` block-mapping form regardless of `width`, which `fleet_scan.parse_sprint_status`'s line-based `_ENTRY` regex also cannot parse — evidence: reproduced live with a 130-char key under the patched `yaml.width=4096` — still read as absent; same root cause as the first finding above.
  - `[medium]` `[patch]` (edge-case-hunter) `test_sprint_plan.py`'s own PEP 723 header declares `requires-python = ">=3.10"`, but the new test transitively execs `scripts/fleet_scan.py`, which does `import tomllib` unconditionally (stdlib only since 3.11) — evidence: confirmed `tomllib` is a 3.11+ stdlib addition and `fleet_scan.py:22` imports it at module level with no guard; under `uv run`, the file's own header governs interpreter selection, so an environment where `uv` resolves the file to Python 3.10 would raise `ModuleNotFoundError` on this file's collection.
  - `[high]` `[patch]` (edge-case-hunter, claim) design-notes/memlog claim that a wide `yaml.width` means the wrap "can never recur" is false for keys ≥128 chars — same root cause and same fix as the first two `high` findings; grouped together.
  - `[low]` `[patch]` (edge-case-hunter, claim) the AC's literal "100-char key" wording vs. the ~85-char key actually used (chosen to dodge the then-unfixed 128-char cliff) — evidence: confirmed the generated key is 84–85 chars, short of 100; resolved as a side effect of the `MAX_SIMPLE_KEY_LENGTH` patch above, which lets the test safely use a literal 100-char key.
  - `[high]` `[defer]` (verification-gap) `bmad-retrospective`'s independent `sprint_status.py::_load_yaml()` factory shares the same file format and the same `fleet_scan.parse_sprint_status` downstream reader but was never given the width fix — evidence: the reviewer reproduced live corruption via `sprint_status.py update` on an unrelated field, silently dropping a long story key from `fleet_scan.parse_sprint_status`'s output. Confirmed real and demonstrated, but the file is not part of this story's declared Surface (only `bmad-sprint-planning` + the two named `SPEC.md`s) — a pre-existing, cross-skill defect, not caused by this diff. `severity: high`.
  - `[low]` `[patch]` (intent-alignment, D1) the intent names both `spec-marshal-single-story-dispatch` and `spec-marshal-token-economy`'s `surface:` lists "via memlog... update," but only the first spec's memlog got an entry — `spec-marshal-token-economy`'s own memlog has no corroborating note explaining why it needs no new surface entries; grouped with the blind-hunter memlog-clarity finding above.
  - `[false]` `[reject]` (intent-alignment, D2) the diff's bug-fix mechanism (`yaml.width` instance attribute, test against `fleet_scan.parse_sprint_status` directly) diverges from the AC's literal wording (`yaml.dump(doc, buf, width=...)` call-site kwarg, test "through the promoter") — evidence: confirmed `ruamel.yaml.YAML.dump()` has no `width` keyword (the Design Notes already document this), and confirmed `scripts/promote_sprint_status.py:189,208,226` has no parsing logic of its own — it loads `scripts/fleet_scan.py` via the identical `importlib.util.spec_from_file_location` mechanism and calls `gen.parse_sprint_status(...)` directly, so testing `fleet_scan.parse_sprint_status` IS testing "through the promoter"; the substitutions are functionally identical, not a divergence.

### 2026-09-09 — Follow-up review pass
- verdicts: 24 findings — high 5, medium 3, low 5, false 8, maybe-false 0, carried 3
- findings:
  - `[high]` `[patch]` (blind-hunter) three D9-amended files edited in the diff (`sprint-status-template.yaml`, `bmad-retrospective/scripts/sprint_status.py`, `test_sprint_status.py`) absent from `spec-marshal-single-story-dispatch` `surface:` — evidence: confirmed SPEC.md listed only the sprint-planning trio from the first pass; patched by adding all three paths + memlog + scoped baseline restamp.
  - `[false]` `[reject]` (blind-hunter) story spec intent-contract still names seven files while epics D9 amended to eleven — evidence: the first pass shipped the original seven-file contract; this follow-up closed the D9 gap without re-deriving `<intent-contract>`; epics AC is the amended oracle.
  - `[medium]` `[defer]` (blind-hunter) story spec `status: done` but ledger key still `backlog` — evidence: confirmed `sprint-status-ledger.yaml:171`; ledger promotion is CAP-4 `sprint-ledger-sync` machinery and was intentionally not run pending steward 48.1; not a code defect in this story's surface.
  - `[medium]` `[patch]` (blind-hunter) frontmatter `deferred:` high item claimed retrospective width fix was never applied — evidence: diff already patches `sprint_status.py` with `yaml.width` + `MAX_SIMPLE_KEY_LENGTH`; removed the stale deferred entry.
  - `[false]` `[reject]` (blind-hunter) Scribe 7.1 stale `docs/reference/` paths untouched — evidence: out of story 31.4 declared Surface; unrelated fleet hygiene.
  - `[false]` `[reject]` (blind-hunter) `test-charter.md` only got governance-currency ignore markers — evidence: out of scope; CAP-6 work belongs elsewhere.
  - `[low]` `[defer]` (blind-hunter, carried) `yaml.Emitter.MAX_SIMPLE_KEY_LENGTH` mutates a shared class attribute — carried: first-pass residual risk still applies; no new cross-module failure observed.
  - `[false]` `[reject]` (blind-hunter) branch bundles Story 33.5 production code — evidence: branch-wide diff envelope; not caused by 31.4 patches in this pass.
  - `[medium]` `[defer]` (blind-hunter) STICKY `blocked` fix ships without `sprint-ledger-sync` — evidence: memlog explicitly records sync deferred until steward 48.1; generator fix is still correct.
  - `[false]` `[reject]` (edge-case-hunter) key length ≥4096 still wraps — evidence: no realistic story key approaches 4096 chars; theoretical only.
  - `[low]` `[defer]` (edge-case-hunter, carried) global `RoundTripEmitter` class mutation — carried from first pass; unchanged risk profile.
  - `[false]` `[reject]` (edge-case-hunter) indented line exceeding `yaml.width` 4096 — evidence: same theoretical ceiling as ≥4096-char keys.
  - `[high]` `[patch]` (edge-case-hunter) `sprint-status-template.yaml` edited but not surface-governed — evidence: grouped with blind-hunter surface gap; fixed in same patch.
  - `[false]` `[reject]` (edge-case-hunter, carried) regenerate/update redump path untested — carried: first pass verified shared `_make_yaml()` factory on load-then-redump by direct reproduction.
  - `[false]` `[reject]` (edge-case-hunter) `_slug()` drift could break 100-char key assertion — evidence: test uses fixed title with `assert len(key) == 100` as sanity guard, not a brittle external dependency.
  - `[low]` `[defer]` (edge-case-hunter) STICKY_STATUSES behavior bundled beyond width fix — evidence: intentional Epic-44 adjacent fix documented in template + memlog; now covered by new blocked test.
  - `[false]` `[reject]` (edge-case-hunter, claim, carried) single-attribute width fix claim — carried: first pass already recorded and accepted.
  - `[false]` `[reject]` (edge-case-hunter, claim) "never change status values" vs STICKY — evidence: STICKY preserves hand-set `blocked`, it does not rewrite ledger values; adjacent fix is intentional.
  - `[false]` `[reject]` (edge-case-hunter, claim, carried) memlog "never recur" absolute wording — carried: memlog already qualifies both ceilings.
  - `[high]` `[patch]` (verification-gap) eleven-file surface incomplete in SPEC + baseline — evidence: baseline JSON lacked all sprint-planning/retrospective/template hashes before restamp; fixed.
  - `[high]` `[patch]` (verification-gap) `STICKY_STATUSES` / `blocked` preservation has no regression test — evidence: searched `test_sprint_plan.py` for `blocked`/`preserved_sticky` before patch — zero matches; added `test_blocked_status_survives_regenerate`.
  - `[low]` `[patch]` (verification-gap) baseline lag after first-pass surface widen — evidence: scoped `--write-baseline --spec pyforge-marshal/spec-marshal-single-story-dispatch` restamped 13 governed files.
  - `[false]` `[reject]` (intent-alignment) branch-wide diff vs narrow story envelope — evidence: descriptive only; 31.4 scoped files are the review target, not the whole branch delta.

## Design Notes

**Why `spec-marshal-single-story-dispatch` and not `spec-marshal-token-economy` for the trio:**
neither spec is thematically "the ledger" by name, but single-story-dispatch's CAP-4 already
triggers `sprint-ledger-sync` on every landing, its Decomposition Record section discusses
`sprint-status-ledger.yaml` state at length, and — decisively — its own `.memlog.md` already
carries the narrative for the 2026-08-31 promote-parser incident (the same bug family this story
permanently fixes) and the still-open 2026-09-06 direction asking for exactly this widening.
`spec-marshal-token-economy` picked up `compile-epic-context.md` for an unrelated reason
(Story 28.8's derived-context layer lives there) and needs no new entries.

**Why `yaml.width`, not `yaml.dump(doc, buf, width=...)`:** `sprint_plan.py` uses
`ruamel.yaml.YAML(typ="rt")`, whose `.dump(data, stream)` method takes no `width` keyword —
`width` is an attribute set on the `YAML()` instance before dumping. The AC's literal snippet
names PyYAML's `yaml.dump(data, stream, width=...)` call shape; the functionally-equivalent
ruamel fix is `yaml.width = 4096` inside `_make_yaml()`, which is read by every dump path since
they all go through that one factory.

## Verification

**Commands:**
- `uv run .claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py` -- expect all
  tests green including the new regression test
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expect green (run once per batch, not
  per story, per the dispatch instructions -- still checked after this story)
- `pixi run -e local-recipes spec-surface-check` -- expect `ok`, zero uncovered/drift
- `python scripts/spec_surface_check.py --write-baseline --spec pyforge-marshal/spec-marshal-single-story-dispatch` -- after surface+memlog land, before commit
- `pixi run -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py -k drift -q` -- generic drift-on-undocumented-edit mechanism (pre-existing, covers the Planted drift matrix row); expect all green

## Auto Run Result

**Summary:** All eleven in-place-edited installer-owned skill files (four `bmad-build-auto` +
three `bmad-sprint-planning` + `sprint-status-template.yaml` + two `bmad-retrospective`) now sit
under marshal spec `surface:` lists — the first pass added the sprint-planning trio; this
follow-up review completed D9 governance for the template and retrospective pair, restamped the
scoped baseline with all thirteen governed paths, removed a stale deferred item (retrospective
width fix was already landed), and added `test_blocked_status_survives_regenerate` for the
Epic-44 `STICKY_STATUSES` / `blocked` preservation bundled in `sprint_plan.py`.

**Files changed (follow-up pass):**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md`
  — `surface:` gains `sprint-status-template.yaml` and the two `bmad-retrospective` paths.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/.memlog.md`
  — decision entry closing the D9 eleven-file pool.
- `.claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py` — new
  `test_blocked_status_survives_regenerate`.
- `scripts/.spec-surface-baseline.json` — scoped restamp for
  `pyforge-marshal/spec-marshal-single-story-dispatch` (13 file hashes + memlog).
- This story spec — follow-up triage log, stale retrospective `deferred:` entry removed,
  `status: done`.

**Review findings breakdown (follow-up pass):**
- **Patched** (5 entries): `high` — complete eleven-file surface + baseline (3 grouped);
  `high` — blocked sticky regression test; `medium` — remove stale retrospective deferred item;
  `low` — baseline lag after first-pass widen.
- **Deferred** (3 entries): `low` — fleet-wide latent wrap-corruption audit (unchanged);
  `low`/`medium` — class-attribute mutation risk + ledger sync timing (carried/deferred).
- **Rejected** (8 entries, `false`): branch-wide diff noise, out-of-scope doc hygiene, theoretical
  ≥4096-char keys, carried first-pass items already settled.

**Follow-up review recommendation: `false`** — forced at HALT for the single allowed follow-up
pass per CAP-11; this pass patched remaining `high` surface/baseline gaps and the blocked test.

**Verification performed (follow-up pass):**
- `uv run .claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py` — 42/42 passed.
- `python scripts/spec_surface_check.py --write-baseline --spec pyforge-marshal/spec-marshal-single-story-dispatch` — stamped 13 files.
- `pixi run -e local-recipes spec-surface-check` — no `uncovered`/`drift` for
  `spec-marshal-single-story-dispatch`.

**Residual risks:** `yaml.Emitter.MAX_SIMPLE_KEY_LENGTH` class-attribute mutation (carried from
first pass); fleet-wide latent wrap-corruption audit still deferred; ledger key remains `backlog`
until operator runs `sprint-ledger-sync` after steward 48.1.
