<!-- RECOVERED 2026-07-25 from a surviving bmad-loop run worktree (.bmad-loop/runs/20260718-101504-2c07/worktrees/6-2-license-axis-producer-gate-flags/_bmad-output/implementation-artifacts/spec-6-10-amendment-design-spike-finding-id-families-verdict-encoding-rung-discriminator-fold-semantics.md); this is the ORIGINAL spec, not an epics.md regeneration. Promoted to tracked planning-artifacts/specs/ for durability. -->
---
title: 'Story 6.10: Amendment design spike — finding-ID families, verdict encoding, rung-discriminator & fold semantics (decision record)'
type: 'chore' # spike — decision record only; no production code, no schema edits
created: '2026-07-18'
status: 'done'
baseline_revision: '5cd8964a45f55243dd1324624f7d29afc90cf1a2'
final_revision: '2236553282f06f404691ce8ca99bd807691f409d'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/prd.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-6-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Story 6.1 (the ComplianceReport schema amendment) is a HARD sprint gate — no other 6.x story may start before it lands — and its own AC requires it to be "a mechanical schema bump, not design work on the critical path." But 6.1's scope list depends on four shapes that do not exist yet and are currently unspecified: the license/currency finding-ID grammars, the typed verdict encoding their policy/waiver/baseline tables must key on, the suppression rung-discriminator (baseline vs waiver) that has no schema representation today (waivers are echoed only in the text renderer, never the JSON contract), and the Gap-B merge/fold semantics for whatever new `Component` fields the amendment adds. Left unresolved, 6.1 either stalls doing ad-hoc design under gate pressure or ships an inconsistent, ungrounded schema.

**Approach:** Run the spike as a pure design/decision exercise (no external tool to probe, unlike Story 1.4's empirical spike) — extend every shipped precedent injectively: the three finding-ID family regexes (`models.py`), the `SeverityTier`-keyed policy-table pattern (`config.py`), the `WaiverNotice`/`apply_waivers` shape (`waiver.py`), and the Gap-B `merge_components`/`_merge_group`/`_fold_bare` mechanism (`inventory.py`). Produce ONE git-tracked decision record in `planning-artifacts/` that pins: (1) the `license:`/`currency:` finding-ID grammars, (2) closed `LicenseVerdict`/`CurrencyVerdict` typed enums + their policy-table shape, (3) the `SuppressedFinding` rung-discriminator shape and its minimal `report-schema.json` placement, and (4) the concrete new `Component` fields (derived from what license/currency coverage-tracking requires) with a per-field Gap-B merge/fold table.

## Boundaries & Constraints

**Always:**
- Spike, not delivery. Touch ZERO production `src/pyforge/warden/` modules and ZERO files under `data/` (`report-schema.json` unedited). The only new tracked deliverable is the decision record markdown under `_bmad-output/projects/pyforge-warden/planning-artifacts/`.
- Every decision cites the existing shipped precedent it extends injectively (file:line) and the FR/AC text it satisfies — no convention invented when a directly analogous shipped pattern exists.
- New finding-ID families use fresh `license:`/`currency:` prefixes, single-line, colon-delimited, sanitized via the existing `_sanitize_id_segment` mechanism (`interfaces.py:119-138`) — never colliding with `vuln:`/`hygiene:`/`indeterminate:`/the exempt `error:` family.
- Typed verdict encoding follows the `SeverityTier`-keyed-policy-table precedent (`config.py:246-263`): one closed `StrEnum` per axis, never raw strings — policy/waiver/baseline tables key ONLY on the enum, never a free-text `indeterminate:` token (closes adversarial-review finding F3).
- The rung-discriminator is a NEW closed 2-value marker (`baseline | waiver`) on a NEW report-schema-contract-level echoed-suppression shape (today's `WaiverNotice` has no discriminator and is echoed only in `render_text`, never JSON) — grounded in the existing `$defs.statusDriver`/`$defs.finding` style.
- The Gap-B table covers every field the record proposes adding to the 13-field `Component` record; each new field is driven strictly by what license/currency coverage-tracking requires (direct analogy to `hygiene_covered`/`vuln_matchable`), and gets an explicit `_merge_group` rule (and a `_fold_bare` rule) using the same conservative "never upgrade confidence" (C0) semantics as the 12 existing merge-group rows.
- The record states its gating scope explicitly: it gates ONLY Story 6.1 (which is itself the transitive HARD gate for 6.2–6.9) — mirroring Story 1.4's explicit "gates 1.5+2.4, not 1.3" disposition line.

**Block If:**
- A required shape cannot be made injective/single-line under `_sanitize_id_segment` without a new escaping rule uncovered by existing tests — HALT `blocked`, name the exact collision.
- No reasonable analogy to an existing shipped pattern exists for a required shape — HALT `blocked` rather than inventing an ungrounded convention, and name the open question.

**Never:**
- No `report-schema.json`, `models.py`, `report.py`, `config.py`, `inventory.py`, `waiver.py`, or any other `src/pyforge/warden/` edits — Stories 6.1/6.2/6.3/6.8 implement.
- No new `Engine`/`Axis` protocol or interface work — OD7 already retired this question (`architecture.md:133`), out of scope.
- No `baseline.py`/`feeds.py`/`actuator.py` design (Stories 6.4/6.8/6.9's job) beyond the one shape 6.10 owns (the rung-discriminator marker itself).
- No `pixi.toml`/dependency changes.

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-warden/planning-artifacts/finding-id-verdict-encoding-decision.md` -- NEW (git-tracked): the decision record; sole deliverable. Consumed by Story 6.1 (and transitively 6.2/6.3/6.8).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/models.py:43-50,231-247,362,422-430` -- READ-ONLY reference: shipped finding-ID family regexes (`_FINDING_ID_FAMILIES`), `StatusDriver` dataclass, global uniqueness enforcement (`ComplianceReport.__post_init__`) — the record extends this injectively.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py:119-138` -- READ-ONLY reference: `_sanitize_id_segment` (escapes `%`, line-boundary chars, `:`) — the injectivity mechanism new families reuse.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/waiver.py:72-76,133-141,330-367` -- READ-ONLY reference: `WaiverNotice` shape + `apply_waivers` two-list split — the record's rung-discriminator design reconciles with this (`baseline.py` doesn't exist yet — Story 6.8's job).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/config.py:118,246-263` -- READ-ONLY reference: the `SeverityTier`-keyed `vuln_severity_policy()` table — the precedent the typed verdict encoding mirrors.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/inventory.py:69-91,222-278,281-371,415-478` -- READ-ONLY reference: the exact-13 `Component` fields + `merge_components`/`_merge_group`/`_fold_bare` (the Gap-B mechanism) the fold table extends.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/data/report-schema.json:5,7-18,263-364` -- READ-ONLY reference: top-level required properties + `$defs` style (`statusDriver`/`finding`/`axisCoverage`) + open `additionalProperties` — the new `$defs` entries must match this style and stay additive.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/osv-db-offline-provisioning-decision.md` -- READ-ONLY reference: the Story 1.4 decision-record structural precedent (frontmatter keys, N-numbered-sections-with-Recommendation/Evidence/Owner spine) this record's format mirrors.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md:452-462,562-572` -- READ-ONLY reference: Story 6.1's frozen scope list + Story 6.10's own AC text this record must satisfy verbatim.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/projects/pyforge-warden/planning-artifacts/finding-id-verdict-encoding-decision.md` -- author the decision record with frontmatter (`title`, `type: 'decision-record'`, `status: 'accepted'`, `created`, `story: '6.10'`, `gates: ['6.1']`, `does_not_gate: ['6.2','6.3','6.4','6.5','6.6','6.7','6.8','6.9']` with a one-line note that these are gated transitively via 6.1 not directly by 6.10, `downstream_owners: ['6.1','6.2','6.3','6.8']`) and a spine covering, per § Design Notes below: (1) the `license:`/`currency:` finding-ID grammars, (2) the `LicenseVerdict`/`CurrencyVerdict` typed encoding + policy-table shape, (3) the new `Component` fields + Gap-B merge/fold table, (4) the `SuppressedFinding` rung-discriminator shape + its `report-schema.json` placement, (5) a worked-examples table proving injectivity and grammar shape, (6) a "how 6.1 applies this" hand-off section (mirroring 1.4's seam hand-off) mapping each pinned decision to the exact 6.1 coordinated-update-set file it lands in -- pins every unspecified shape 6.1 needs so 6.1 implements with zero new design decisions.

**Acceptance Criteria:**

*(Story 6.10 ACs from `epics.md`, preserved verbatim — the contract of record.)*

**Given** the 6.1 scope list, **when** the spike completes, **then** a committed decision record (planning-artifacts) pins: the license/currency finding-ID family grammars (single-line, colon-delimited, injective — same rules as the three shipped families) and the typed verdict encoding (schema-validated fields policy/waivers/baselines key on); the suppression rung-discriminator shape (a closed `baseline | waiver` marker on echoed suppressions); and the Gap-B merge/fold table for every new `Component` field (conservative C0 semantics per field, `_merge_group`/`_fold_bare` positions named).

**Given** the decision record, **when** 6.1 executes, **then** 6.1 implements it without new design decisions — 6.1 remains the sole schema writer and the HARD gate (one amendment, one bump; this spike changes no code and no schema).

## Design Notes

**Decision-record spine (6 sections — grounded recommendations the implementer expands into prose). Amended 2026-07-18 after review pass 1 — see `## Spec Change Log`; every numbered fix below is load-bearing, not stylistic, and must be applied by the re-derivation, not merely acknowledged:**

1. **License finding-ID grammar.** `license:<spdx-expression-or-"unknown">:<pkg>@<ver>` — regex `license:[^:\n]+:.+@.+`, matching the shipped `vuln:` shape exactly (component@version tail). Segment 2 is the SPDX expression itself (or literal `unknown` when unresolvable) — the injective "why," analogous to `vuln:`'s advisory-id. **Fix 1 (was factually wrong):** do NOT claim SPDX expressions never contain colons — SPDX's `DocumentRef-<idstring>:LicenseRef-<idstring>` syntax (a standard SPDX License List Matching Guidelines construct for custom license refs) legitimately embeds a literal `:`. `_sanitize_id_segment` (`interfaces.py:119-138`) is therefore **load-bearing, not defensive**, for this family — state that explicitly, and state that it applies to **every** segment the producer supplies (segment 2 AND the `<pkg>@<ver>` tail), mirroring `vuln.py:725-757`'s full-segment sanitization, not just segment 2. The literal token `unknown` intentionally collides with a component whose SPDX metadata literally contains the legacy setuptools string `"UNKNOWN"` — both denote "no reliable SPDX identifier available," so the collision is semantically correct, not a bug; say so in one sentence rather than leaving it unaddressed. A finding is emitted only for `denied`/`unknown` verdicts — never for `allowed` (matches the "findings exist only for problems" invariant already true of hygiene/vuln); the schema must enforce this — see Fix 6 below.

2. **Currency finding-ID grammar.** `currency:<reason>:<subject>@<ver>` — regex `currency:[^:\n]+:.+@.+`. `<reason>` ∈ `{eol, over-lag, unknown}` (free-text-but-typed by producer code, same convention as `hygiene:`'s DEP-code segment — not regex-enumerated); **Fix 2 (new — precedence):** state an explicit precedence when a component is simultaneously `eol` and beyond `--max-lag`: the reason token is `eol` (the more severe/terminal classification), with the numeric `lag` field still populated on the finding for transparency even though `eol` wins the reason-token slot. **Fix 3 (was a real collision risk):** `<subject>` is `<pkg>` for a component; for the FR34 first-class runtime-currency field, do NOT use the bare literal `runtime-python` — a real PyPI/conda package could legitimately be named `runtime-python` (PEP 508/503's package-name grammar `[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?` permits it), producing an indistinguishable id collision. Use the reserved sentinel `!python-runtime` instead — `!` is not a legal character in any PyPI or conda package name, so this token is structurally uncollidable with any real component subject. Both shapes still fold into the same `X@Y` tail the regex expects. A finding is emitted only for `eol`/`over-lag`/`unknown` — never for a clean `supported`-with-no-lag component.

3. **Typed verdict encoding.** Two new CLOSED `StrEnum`s in `models.py` (co-located with `Status`/`CveMatchLevel`/`WithholdReason`, but NOT added to the sanctioned-growable list — FR32/FR34 each pin exactly 3 values with no stated growth path, so closed, additively-widenable-only-via-schema-bump like `Status` itself): `LicenseVerdict = {ALLOWED="allowed", DENIED="denied", UNKNOWN="unknown"}`; `CurrencyVerdict = {SUPPORTED="supported", EOL="eol", UNKNOWN="unknown"}`. `EffectiveConfig` gains `license_policy`/`currency_policy` as `@property` (mirroring `vuln_severity_policy`'s actual shape at `config.py:245-263` — a property, not a callable method) returning `dict[LicenseVerdict|CurrencyVerdict, Status]`. **Fix 4 (wrong citation):** this closes adversarial-review finding **F1**, not F3 — `architecture.md:134` attributes this exact "policy tables key ONLY on these [typed fields]" item to F1 ("closes adversarial F1"); F3 is the unrelated post-verdict `actuation` section. **Fix 5 (unclear wording — read by reviewers as self-contradictory):** reword away from "policy tables key exclusively on verdict members" in isolation. State precisely: the **closed verdict enum** is the only thing free-text policy/waiver/baseline **matching** may key on (closing the smuggle path); a **numeric threshold comparison** (`lag` vs `--max-lag`) is a second, additive escalation input Story 6.5 evaluates alongside the verdict-keyed table lookup, not a competing free-text mechanism — both together decide the final rung for a `CurrencyVerdict.SUPPORTED` finding. `CurrencyVerdict` itself stays exactly `supported`/`eol`/`unknown` (3 values); `over-lag` is never a 4th member.

4. **New `Component` fields + Gap-B fold table.** Exactly two new boolean fields, mirroring `hygiene_covered`'s binary "was this axis even attempted" semantic (not `vuln_matchable`'s match-strength semantic — `vuln_matchable`'s actual formula additionally gates on `pypi_identity is not None`, `inventory.py:342-345`, not a pure AND like `hygiene_covered`; license/currency resolution has no multi-tier confidence, only pre-build-metadata-available-or-not, so plain AND is correct for the two new fields specifically):

   | New field | Type | `_merge_group` rule | `_fold_bare` rule |
   |---|---|---|---|
   | `license_covered` | `bool` | AND (both merged records must be covered) | AND |
   | `currency_covered` | `bool` | AND | AND |

   Both rules match the existing `hygiene_covered` AND-row verbatim (conservative C0: merging/folding never upgrades coverage confidence). State the accurate pre-existing count **once**: `Component` has 13 fields total — 11 carry a real `_merge_group` reducer, 2 (`ecosystem`, `version`) are identity-invariant pass-throughs copied from `group[0]` because they're literally part of the group's identity key — do not relitigate this count more than once in the record. **Fix 6 (new — implementation pitfall):** `_fold_bare` (`inventory.py:415-478`) builds its result via `dataclasses.replace(concrete, **changes)`, NOT a full `Component(...)` constructor call like `_merge_group` — flag explicitly that 6.1's implementer MUST include `license_covered=...`/`currency_covered=...` in the `replace()` kwargs; omitting them silently carries over `concrete`'s existing value instead of applying the AND-fold (no missing-arg error, since `replace()` doesn't require exhaustive kwargs) — recommend a dedicated meta-test asserting the folded result differs from `concrete` in a synthetic AND-should-flip-false fixture. **Fix 7 (new — ownership gap):** name explicitly that Story 6.5 (the escalation-mapping owner) is responsible for emitting an `indeterminate:uncovered:<pkg>`-style finding when `license_covered`/`currency_covered` is `False`, by direct analogy to the existing coverage-driven pattern `interfaces.py:62-71` documents for `hygiene_covered`/`vuln_matchable` — an uncovered component must never compose a rung silently. The actual per-component license/currency verdict data (SPDX expression, tier, lag, eol_date) lives on the `Finding`, not on `Component` — `Component` only tracks assessability.

5. **Suppression rung-discriminator + schema placement.** New `$defs.suppressedFinding`: `{finding_id: str, source: "baseline"|"waiver", reason: str, authorized_by: str|None, expires_at: str|None}` — reuses `WaiverNotice`'s 4 fields (`id`→`finding_id` to disambiguate against `$defs.finding.id`) plus the new closed 2-value `source` discriminator. **Fix 8 (unjustified deviation):** `authorized_by`/`expires_at` are nullable here while `WaiverNotice` (`waiver.py:133-141`) declares both required — state the justification explicitly rather than silently claiming "verbatim" reuse: baseline entries (Story 6.8, FR39) are accepted in bulk via one committed `.warden-baseline.yaml` file rather than individually signed like a waiver, so a per-entry `authorized_by` may legitimately be absent for `source: "baseline"`; full validation-rule design for `baseline.py` stays out of scope (already correctly noted in Residual Risks) but this one sentence of justification belongs in § 5 itself, not only in Residual Risks. **Fix 9 (new — schema completeness, FR34 gap):** the `currency` sub-object is missing a `latest` field — FR34 (`prd.md:565`) requires it alongside `lag`/`eol_date`/`tier`; add `"latest": {"type": ["string", "null"]}`. **Fix 10 (new — schema coherence):** add an `allOf`/`if`/`then` clause forbidding `Finding.license.verdict == "allowed"` when `Finding.id` matches `^license:`, mirroring the existing `vuln:`/`hygiene:` axis-coherence clauses (`report-schema.json:320-339`) — otherwise the schema validates a document whose id says "problem" and payload says "clean," which never happens per § 1's own emission rule but the schema doesn't say so. **Fix 11 (new — invariant, document even if not JSON-Schema-enforceable):** state as a documented MUST-hold invariant that `suppressions[]` carries **at most one** entry per `finding_id`, with waiver winning the tie-break where both a baseline and a waiver match the same finding (per `architecture.md:314`'s "echoed once" rule) — Story 6.1/6.8 enforce this in code (Draft 2020-12 has no native cross-array uniqueness-by-key keyword), analogous to how `ComplianceReport.__post_init__` already enforces global `finding.id` uniqueness. **Fix 12 (new — recommend a cross-check):** recommend Story 6.1 add a `ComplianceReport.__post_init__` check that every `suppressions[].finding_id` references an existing `findings[].id`, mirroring the rigor `StatusDriver` already gets. **Fix 13 (unresolved forward reference):** the open question of who wires the existing `cli.py` waiver-echo path into the new JSON `SuppressedFinding` model must get an actual recommendation in this section, not a forward reference to another section that never delivers it: recommend Story 6.1 (which already owns `models.py`/`report-schema.json` in this commit) wires the waiver-echo half (`WaiverNotice` → `SuppressedFinding{source:"waiver"}` inside `cli.py`'s existing render path), while Story 6.8 wires the baseline half (`SuppressedFinding{source:"baseline"}`) since baseline entries don't exist until 6.8 lands — and this decision must also be carried into Residual Risks if any part of it stays genuinely open. New top-level optional `ComplianceReport` field `suppressions: [SuppressedFinding]`, parallel in shape to `findings`, additive (`additionalProperties` stays open, `test_additive_extra_fields_still_validate` unaffected).

6. **Worked examples (prove injectivity + grammar shape):** update the table to use `!python-runtime` (Fix 3) in place of `runtime-python`, and add one row demonstrating the Fix 2 EOL/over-lag precedence (a component both EOL and over-lag resolves to `currency:eol:...`, not `currency:over-lag:...`). Whatever the final row count is, do not state a specific count in prose elsewhere (e.g. "these N worked examples") unless it is re-verified against the actual table at write time — a prior draft of this record said "five" against an actual six-row table.

**Fix 14 (new — give the waiver.py gap a recommendation, not just an open question):** the record's finding that `waiver.py:68-76` locally re-declares `_FINDING_ID_FAMILIES` and is absent from `epics.md`'s Story 6.1 coordinated-update-set is correct and must stay — but end it with an actual recommendation rather than "this record does not pick one": recommend widening `waiver.py`'s local tuple in the **same commit** as Story 6.1's `models.py` widening (Story 6.1 already touches the sibling tuple; the marginal cost of also touching `waiver.py`'s one-line mirror is near-zero next to the risk of 6.2 shipping license: findings that are constructible but unwaivable, directly contradicting Story 6.8's own AC text).

**Fix 15 (citation correction):** "How Story 6.1 applies this" item 3 must cite `report.py:319` (`jsonschema.Draft202012Validator(_packaged_schema()).validate(document)`, inside `render_json`) for "self-validation," not `report.py:143-156` (that range is `REPORT_SCHEMA_VERSION`/`_REPORT_AXES`/`_packaged_schema()` — the loader, not the validator).

**Fix 16 (unsupported claim):** the "Fixtures" subsection must not claim `Component`'s dataclass carries a `True` default for `hygiene_covered`/`vuln_matchable` — `Component` (`inventory.py:69-91`) is a defaultless frozen dataclass; the `True`/computed defaults actually live in the test-fixture factory `tests/conftest.py:46-58` (`make_component()`), and `vuln_matchable`'s fixture default is not a flat `True` — it's computed from `pypi_identity`/`indeterminate_reason`. Cite the fixture factory, not the dataclass, for this claim.

**Why no empirical evidence table (unlike 1.4):** this spike has no external tool to probe — every shape is derived by direct, cited analogy to already-shipped, already-tested code (`models.py`'s regex family, `config.py`'s policy-table pattern, `inventory.py`'s merge/fold rows, `report-schema.json`'s `$defs` style). The record's "Evidence" per section is that citation, not a measurement.

**KEEP instructions (from review pass 1 — these worked and must survive re-derivation unchanged in spirit):** the overall decision-record structure (a numbered spine of Recommendation+Evidence+Owner sections, a "How Story 6.1 applies this" coordinated-update-set hand-off section, a closing Residual Risks section) mirrors the Story 1.4 precedent well and should be kept; the practice of citing exact file:line evidence for every claim (verified extensively accurate in review) must continue for every claim, including the 16 fixes above; the frontmatter shape (`gates`/`does_not_gate`/`downstream_owners`) was correct and unchanged; the "12 vs 13" and "`@property` not method" corrections the first draft made on its own were good catches — keep that self-critical grounding instinct, just fold each correction in once instead of restating it.

**Review pass 2 amendment (2026-07-18) — CRITICAL: pass-1's re-derivation introduced a fabricated citation and dropped real content pass-1 had. Read this whole block before writing anything, and verify every symbol/line citation yourself via a real grep/read before using it — do not transcribe a citation from this list without confirming it, and do not invent a new one either.** Fixes 17–35 below are all independently verified against the live source this round (exact commands used are noted so you can re-run them):

17. **Citation must name the real function.** The `vuln.py` full-segment-sanitization precedent function is **`_findings_for_package`** (`vuln.py:699-730`), not `_finding_from_group` — `grep -rn "_finding_from_group" src/shared/packages/pyforge-warden/` returns zero hits; that name does not exist anywhere in the repo. Inside it: `name_segment = _sanitize_id_segment(pkg_name)` (`vuln.py:725`) and `version_segment = _sanitize_id_segment(pkg_version) if isinstance(pkg_version, str) and pkg_version else "unspecified"` (`vuln.py:726-729`) — note the version segment is NOT unconditionally sanitized; it falls back to the literal token `"unspecified"` when `pkg_version` is missing/non-string, checked BEFORE sanitizing, not relying on sanitize's own internal fallback (see Fix 30/31).

18. **The "breaks `.fullmatch`" mechanism claim is factually wrong — remove it.** Verified directly: `python3 -c "import re; print(re.compile(r'license:[^:\n]+:.+@.+').fullmatch('license:DocumentRef-vendor:LicenseRef-my-custom-1.0:acme-widget@2.0.0'))"` **succeeds** (backtracking finds a valid split) — an unescaped colon does NOT break `.fullmatch`. State the real risk instead: an unescaped colon breaks id **injectivity/stability** (two different underlying values could stringify ambiguously) and breaks any consumer that manually `.split(":")`s an id instead of treating it as an opaque string — waiver matching (`waiver.py`'s dict lookup by the whole `finding_id` string) is NOT such a consumer and is unaffected either way; do not claim it is.

19. **`_REPORT_AXES` scope was wrong — it DOES change in 6.1.** "How Story 6.1 applies this" item 3 must not say `_REPORT_AXES` is unchanged. `epics.md:460` — the exact text this record cites elsewhere as the authoritative "coordinated update set" — literally lists "`report.py` runtime self-validation **+ `_REPORT_AXES`**" as part of Story 6.1's scope. `_REPORT_AXES` grows to include `"license"`/`"currency"`. Also: verify yourself whether `report.py` today has any "fails loud on a coverage claim for an unregistered axis" check (architecture.md calls this F6) — if it does not exist yet, say so plainly and name it as something Story 6.1 must build, not just widen a tuple.

20. **Add a `license` sub-object schema draft — one didn't exist.** §5 (pass 2) drafted a `currency` JSON sub-object but no analogous `license` one, despite the coherence clause referencing `Finding.license.verdict`. Add: `{"oneOf": [{"type":"null"}, {"type":"object","required":["expression","verdict"],"properties":{"expression":{"type":"string"},"family":{"type":["string","null"]},"verdict":{"enum":["allowed","denied","unknown"]}}}]}` — do NOT add a `source` field here (that would collide with Fix 24's renamed discriminator AND with the separate report-section-level `{source,snapshot_at,max_age_ok}` provenance epics.md:460 already assigns to the `license`/`currency` report *sections*, a different level than a per-finding sub-object).

21. **Restore the axis-coherence content pass 1 had and pass 2 dropped, and extend it to `report-schema.json` too.** Pass 1's draft had a paragraph titled "A finding for Story 6.1 beyond the two new regex entries" extending `ComplianceReport.__post_init__`'s per-family axis cross-check (the existing `if finding.id.startswith("vuln:") and finding.axis != AXIS_VULNERABILITY: raise ...` / `hygiene:` pattern — re-read `models.py` yourself to get the current exact line numbers, do not assume pass 1's) with two new parallel clauses for `license:`→`axis=="license"` and `currency:`→`axis=="currency"`. Pass 2 silently dropped this paragraph. Restore it. Additionally add the schema-level mirror: two new `allOf`/`if`/`then` clauses in `report-schema.json` alongside the existing `vuln:`/`hygiene:` pair (re-read `report-schema.json` yourself for the current exact lines — do not reuse a stale line number from an earlier draft) enforcing the same id-prefix ↔ axis coherence at the JSON-Schema level, not just in Python.

22. **Add a currency id-reason ↔ verdict coherence clause (new value-add, not previously specified — derivable now from Fix 2/6's already-pinned precedence rule).** Since §2 pins the precedence `eol` > `over-lag` > `unknown` for the id's reason segment, the mapping to `CurrencyVerdict` is now fully determined: id reason `eol` ⟹ `verdict: "eol"`; id reason `unknown` ⟹ `verdict: "unknown"`; id reason `over-lag` ⟹ `verdict: "supported"` (escalation lives in the numeric `lag` field, not the verdict — per Fix 5/§3). Add one `allOf`/`if`/`then` triple encoding this, mirroring the license coherence clause's style.

23. **Ownership correction — this record's own pass-1 Fix 7 was wrong; the "uncovered" finding is Story 6.1's job, not Story 6.5's.** Verified: `interfaces.py:349-383` shows the analogous `hygiene_covered`-driven `indeterminate` finding (`if not component.hygiene_covered: derived.append((Status.INDETERMINATE, "uncovered", AXIS_HYGIENE, ...))`) is **unconditional composition logic inside `DefaultPolicy`'s per-component loop** — it runs regardless of any axis-gating configuration. Story 6.5's charter (`epics.md:504-514`, "Two-mode policy integration") is specifically the warn↔policy-violation escalation mapping for **gated** axes — a different, later concern. The correct owner is **Story 6.1**, which must extend `DefaultPolicy`'s per-component loop (`interfaces.py`) with two new parallel `if not component.license_covered: derived.append(...)` / `if not component.currency_covered: derived.append(...)` blocks mirroring the existing `hygiene_covered` block exactly. Correct every "Owner: ... Story 6.5" attribution for this specific finding to "Story 6.1"; Story 6.5 keeps its correct, separate ownership of the escalation-mapping composition (§3).

24. **Rename the `SuppressedFinding` discriminator field — `source` collides with an existing, semantically different key.** Verified: `report-schema.json:87` already has `VulnData.source: {"type": ["string", "null"]}` — a free-text, nullable data-provenance string, and `epics.md:460` assigns the SAME `{source, snapshot_at, max_age_ok}` shape to the new `license`/`currency` report *sections* too. Reusing the key name `source` for `SuppressedFinding`'s closed 2-value categorical discriminator creates two unrelated meanings for one key name in the same document/schema — exactly the ambiguity the `id`→`finding_id` rename (§5) was meant to avoid. Rename to **`origin`**: `SuppressedFinding{finding_id, origin: "baseline"|"waiver", reason, authorized_by, expires_at}`. Propagate this rename everywhere `source` was used for this discriminator (schema draft, worked examples, prose, "How Story 6.1 applies this").

25. **`downstream_owners` frontmatter must include Story 6.5.** The record's own body (§3: "Owner: ... Story 6.5 (the composed escalation mapping, both inputs)") names Story 6.5 as an owner, but the frontmatter list omits it. Set `downstream_owners: ['6.1', '6.2', '6.3', '6.5', '6.8']`.

26. **Soften the "resolved, nothing stays open" framing for the `cli.py`/`waiver.py` wiring — it overclaims.** The record says "Nothing about this wiring stays open" and then immediately concedes `cli.py` isn't in `epics.md:460`'s literal "exactly" file list and floats a future `bmad-correct-course`. Both things can be true without contradiction if worded honestly: keep the concrete recommendation (Story 6.1 wires the waiver half via `cli.py`; widens `waiver.py`'s local tuple in the same commit), but say plainly that this is a **recommended, common-sense minor scope extension** of Story 6.1's AC (not literally pre-approved by the AC's exact file list), and that the story's own dev notes should flag it rather than silently exceed the AC. Do not claim "resolved, nothing stays open" and then walk it back in the same document.

27. **Pin `lag`'s unit — never specified despite a precedence rule depending on it.** State explicitly: `lag` is an integer count of **releases behind the latest available release**, not a day/calendar-time count — chosen because `--max-lag <n>` reads naturally as a release-count threshold, and a separate, already-named concept (`max_age_ok`, the bundled-data staleness field per NFR-S9) already owns the day/calendar-time axis, so `lag` would be redundant with it if also time-based. When a verdict derives from a date-based ladder tier (endoflife.date), Story 6.3's producer computes an equivalent release-count approximation for `lag`; when it derives from a release-position tier (N/N-1 channel data), `lag` is exact.

28. **Citation precision — two different functions, two different line ranges.** `_finding_sort_key` is `models.py:520-538`; `_coverage_sort_key` starts separately at `models.py:541` (re-verify the exact end line yourself) — cite them as two ranges, not one combined range.

29. **Don't over-read the `waiver.py:80-83` comment.** That comment is about length-bound symmetry between `authorized_by` (200 chars) and `reason` (1000 chars), not an explicit statement of "per-person accountability." If the nullability-justification paragraph (§5) wants to make an accountability point, ground it in the field's own name/type/required-ness instead of over-attributing intent to that specific comment.

30. **Pin the version-tail convention explicitly, mirroring the verified `vuln.py` precedent (Fix 17).** State that `license:`/`currency:` findings use the exact same version-segment convention as `vuln:`: `_sanitize_id_segment(component.version) if component.version else "unspecified"`, checked BEFORE sanitizing (not relying on `_sanitize_id_segment`'s own internal empty-string fallback for this position specifically) — so a component with no resolved version still gets a well-formed finding id using the literal `unspecified` tail segment.

31. **Guard against an `unknown`/`unspecified` token collision — a real, verified risk.** `_sanitize_id_segment` (`interfaces.py:119-138`) has its own internal behavior: `return escaped if escaped else "unspecified"` (`interfaces.py:136`) — an empty string degrades to the literal token `unspecified`. This is DIFFERENT from and must not collide with the intentional `unknown` token §1 already pins for "resolution genuinely failed." State explicitly: the license/currency producer must never pass an empty string `""` to `_sanitize_id_segment` for the expression/reason segment — always resolve to the literal `unknown` token FIRST, the same way `vuln.py`'s version-segment logic decides the fallback before calling sanitize rather than depending on sanitize's own fallback (Fix 17/30). This keeps `unknown` (intentional "we don't know") and `unspecified` (would only appear as a symptom of a producer bug) from ever meaning the same thing on the same segment.

32. **Footnote the inherited, extremely-low-probability `!python-runtime` collision (Residual Risks, not a redesign).** `_sanitize_id_segment` does not escape `!` either. The `!python-runtime` sentinel (§2) is collision-free against any REAL PyPI/conda registry name (which cannot legally contain `!`), but not against a hypothetical `RAW_MALFORMED`-mode component whose garbage-extracted name happens to literally contain the string `!python-runtime`. One sentence in Residual Risks acknowledging this is enough — this is not worth a redesign.

33. **Clarify `--bypass` is out of `SuppressedFinding`'s scope (a real, verified, distinct mechanism) — do not add a 3rd `origin` value for it.** Verified: `bypass_blocking` (`waiver.py:370-388`) is explicitly documented as "the CLI's blanket suppression, distinct from a real waiver file's exact-id matching" — a transient, whole-run override mapping affected findings straight to the existing `Status.BYPASSED` rung (already a first-class lattice member), not a persistent per-finding suppression source. `emit_bypass_stanza` (`waiver.py:442-...`) prints a DRAFT `.warden-waivers.yaml` stanza a human may choose to commit — only once actually committed would the same finding later appear via `SuppressedFinding{origin="waiver"}` in a *subsequent* run. Add one paragraph (§5 or Residual Risks) stating this explicitly: `origin`'s closed 2-value set (`baseline`/`waiver`) is correct as scoped by `epics.md`/`architecture.md`'s literal "baseline vs waiver echo" text; `--bypass` is a different, pre-existing mechanism, never named as a third suppression source in any FR/AC this spike is chartered against.

34. **Name the real production `Component(...)` construction sites — the implementation map was incomplete.** Verified via `grep -rln "Component(" src/shared/packages/pyforge-warden/src/pyforge/warden/ src/shared/packages/pyforge-warden/tests/`: besides `inventory.py` (`_merge_group`/`_fold_bare`) and `tests/conftest.py` (`make_component`), production code in **`extract/pyproject.py`** and **`extract/_identity.py`** also constructs `Component(...)` directly and needs the two new fields added. `sbom.py` and the two test files (`test_models.py`, `test_vuln.py`) also matched the grep — read each yourself to determine whether it constructs a NEW `Component` (needs updating) or only reads/re-exports an existing one (does not), and state which is which rather than assuming.

35. **Add a light schema-completeness guard for currency provenance (pairs naturally with Fix 22).** Add an `if`/`then` requiring `latest`/`lag`/`eol_date` be non-null when `currency.verdict` is `"eol"` or when the id's reason segment is `over-lag` (i.e., whenever there is a "problem" to explain) — `null` stays allowed only for `unknown`/a clean `supported`-with-no-lag state (which, per §2, never produces a finding at all, so this mostly matters for the `eol`/`over-lag` cases).

**KEEP from pass 2 (the parts that were right — do not lose these in the rewrite):** the 8-row worked-examples table structure and its "what it proves" column; the `_fold_bare`/`dataclasses.replace()` omission-trap paragraph and its recommended flip-detecting meta-test; the `Component`-defaults correction (citing `tests/conftest.py`, not the dataclass); the `waiver.py:68-76` same-commit recommendation (§7); the F1-not-F3 citation correction (this one WAS verified correct — `architecture.md:134` does say "closes adversarial F1"); the two-input (verdict-table + numeric-lag) escalation-composition explanation in §3 (correct in substance, just needs the `origin` rename propagated and no other change).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all existing suites pass unchanged (zero production `src/` edits, zero schema edits — this spike cannot regress anything). `--frozen` is required in this bmad-loop worktree per the path-length pixi-build-python panic documented in `deferred-work.md`; unfrozen fails environmentally regardless of this spike's content. Verified: 1227 passed.

**Manual checks (no CLI for the deliverable itself):**
- `_bmad-output/projects/pyforge-warden/planning-artifacts/finding-id-verdict-encoding-decision.md` exists, is git-tracked (`git status` shows it as new/tracked, not under gitignored `implementation-artifacts/`), and covers all 6 § Design Notes topics with a grounded recommendation + cited evidence per topic.
- Every finding-ID example in the record's worked-examples table parses under its stated family regex and is distinct from every other example (visual injectivity check — no dedicated test exists since no code ships).
- The record states its gating scope (`gates: ['6.1']` only, transitive to 6.2–6.9) matching the "gates 1.5+2.4, not 1.3" precedent framing.

## Spec Change Log

### 2026-07-18 — Review pass 1 (bad_spec loopback)

Triggering findings: 9 bad_spec findings from Blind Hunter + Edge Case Hunter, all root-caused in this spec's own Design Notes (not in `<intent-contract>`, which needed no change): (1) `<subject>` literal `runtime-python` for the FR34 runtime-currency field is not collision-proof against a real PyPI package of the same name; (2) the claim "SPDX expressions never contain colons" is factually wrong (SPDX's `DocumentRef:LicenseRef` syntax embeds one), understating `_sanitize_id_segment` as merely defensive when it is load-bearing; (3) § 3 mislabeled the closed adversarial-review finding as F3 when `architecture.md:134` attributes it to F1; (4) the currency `Finding` sub-object omitted the FR34-mandated `latest` field; (5) `authorized_by`/`expires_at` were made nullable on `SuppressedFinding` without justification against `WaiverNotice`'s required fields; (6) no precedence was pinned for a component that is simultaneously `eol` and `over-lag`; (7) § 3's "policy tables key exclusively on verdict members" reads as excluding the numeric `lag`-threshold escalation path entirely, an apparent self-contradiction; (8) only segment 2 was explicitly named for `_sanitize_id_segment` treatment, not the full `<pkg>@<ver>` tail; (9) the literal token `unknown` colliding with a legacy setuptools `"UNKNOWN"` license-metadata artifact was left unacknowledged.

Known-bad state avoided: Story 6.1 implementing this record verbatim would have shipped (a) a real, exploitable finding-ID collision between the Python runtime and any real package named `runtime-python`; (b) a schema that cannot carry a FR34-required field, forcing a second amendment outside 6.1's "one sanctioned amendment" charter; (c) ambiguous escalation logic for over-lag currency findings; (d) a documented rationale that undersells why sanitization is mandatory, risking a future producer skipping it.

Amendment: rewrote the 6-topic Design Notes spine in place, folding in 16 numbered fixes (Fix 1–16, inline above) covering all 9 bad_spec findings plus 7 additional patch-level findings bundled into the same re-derivation pass for efficiency (see Review Triage Log below for the full patch list — these were not individually reprocessed as separate patches since a full re-derivation was already required). No content inside `<intent-contract>` was touched; the Problem/Approach/Boundaries/Never sections remain exactly as originally derived from `epics.md`'s Story 6.10/6.1 AC text.

KEEP instructions for re-derivation: preserve the overall decision-record structure (numbered Recommendation+Evidence+Owner sections, the "How Story 6.1 applies this" hand-off section, the closing Residual Risks section) — this mirrors the Story 1.4 precedent well; preserve the practice of citing exact file:line evidence for every claim (independently verified extensive and accurate in review); preserve the frontmatter shape (`gates`/`does_not_gate`/`downstream_owners`) unchanged; preserve the self-critical instinct that caught the "12 vs 13" count and the `@property`-vs-method issues on the first pass, but state each correction once, not repeatedly.

### 2026-07-18 — Review pass 2 (bad_spec loopback)

Triggering findings: 19 findings (Fix 17–35, inline above) from a second Blind Hunter + Edge Case Hunter pass against the pass-1-corrected draft. Root causes split roughly evenly between (a) gaps in this spec's own pass-1 amendment — the `Story 6.5` uncovered-finding misattribution (this spec's own Fix 7), the never-pinned `lag` unit, the `--bypass`/`SuppressedFinding` scope question never researched, the incomplete `extract/*.py` Component-construction-site survey, the `source` key naming collision never checked against the rest of the schema — and (b) the pass-1 re-derivation's own execution errors: a fabricated citation (`_finding_from_group`, a function that does not exist — confirmed via `grep -rn` returning zero hits) presented as "independently re-verified," an empirically false claim about how an unescaped colon "breaks `.fullmatch`" (verified false by actually running the regex), and — most concerning — a regression, where pass 1's draft correctly extended `ComplianceReport.__post_init__`'s per-family axis cross-check for the two new families and pass 2's rewrite silently dropped that content.

Known-bad state avoided: Story 6.1 implementing pass 2's record verbatim would have (a) shipped `_REPORT_AXES` unchanged, missing an AC requirement the same document cites elsewhere as authoritative; (b) left the two new families without axis-coherence enforcement (a mis-axed `license:`/`currency:` finding would construct silently, unlike every other family); (c) assigned the "uncovered" finding to the wrong story (Story 6.5), which doesn't own the composition code path that actually needs to change; (d) shipped a schema field name (`source`) that collides in meaning with an existing key in the same document; (e) left `lag`'s unit ambiguous, undermining the very precedence rule the record exists to pin; (f) left an unresearched open question about whether `--bypass` needs its own suppression-source value; (g) missed 2 real production call sites that construct `Component` directly and would break without the new fields.

Amendment: appended a "Review pass 2" addendum to Design Notes (19 numbered fixes, each with independently-verified evidence — exact commands/greps recorded so the next pass can re-run them rather than trust them blindly) plus a "KEEP from pass 2" list naming exactly which parts of the pass-2 draft were verified correct and must survive. Explicit instruction added at the top of the addendum: verify every citation via a real tool call before using it; do not transcribe without confirming.

KEEP instructions for re-derivation (this pass): everything from pass 1's KEEP list, plus: the 8-row worked-examples table structure; the `_fold_bare`/`replace()` omission-trap paragraph and its flip-detecting meta-test recommendation; the `Component`-defaults correction (`tests/conftest.py`, not the dataclass); the `waiver.py:68-76` same-commit recommendation; the F1-not-F3 correction (re-verified correct again this pass); the two-input escalation-composition explanation in §3 (correct in substance, needs only the `source`→`origin` rename propagated).

## Review Triage Log

### 2026-07-18 — Review pass 1
Blind Hunter (`bmad-review-adversarial-general`) and Edge Case Hunter (`bmad-review-edge-case-hunter`) ran in parallel against the new decision-record file (the sole diff). Both independently verified the overwhelming majority of the record's file:line citations as accurate. 9 findings root-caused in this spec's own Design Notes, triggering a bad_spec loopback; the remaining 12 findings were decision-record-original elaboration gaps, bundled into the same spec amendment (see `## Spec Change Log`) rather than processed as separate patches, since a full re-derivation was already required.
- intent_gap: 0
- bad_spec: 9: (high 3, medium 5, low 1)
- patch: 12: (high 1, medium 4, low 7)
- defer: 0
- reject: 0
- addressed_findings:
  - `[high]` `[bad_spec]` `<subject>` literal `runtime-python` for the FR34 runtime-currency finding is not collision-proof against a real PyPI/conda package of the same name (PEP 508/503 permits it) — spec now pins the reserved sentinel `!python-runtime` (`!` is not a legal PyPI/conda name character).
  - `[high]` `[bad_spec]` Spec's Design Notes claimed "SPDX expressions never contain colons," which is false (SPDX `DocumentRef:LicenseRef` syntax embeds one) — spec now states `_sanitize_id_segment` is load-bearing, not defensive, for the `license:` family, applied to every segment.
  - `[high]` `[bad_spec]` Currency `Finding` sub-object omitted the FR34-mandated `latest` field entirely — spec now adds it to the schema draft.
  - `[medium]` `[bad_spec]` § 3 mislabeled the closed adversarial-review finding as F3; `architecture.md:134` attributes it to F1 — spec corrected.
  - `[medium]` `[bad_spec]` `SuppressedFinding.authorized_by`/`expires_at` made nullable with no justification against `WaiverNotice`'s required fields — spec now states the baseline-vs-waiver rationale explicitly in § 5 itself.
  - `[medium]` `[bad_spec]` No precedence pinned for a component simultaneously `eol` and `over-lag` — spec now pins `eol` as the winning reason token.
  - `[medium]` `[bad_spec]` § 3's "policy tables key exclusively on verdict members" read as excluding the numeric `lag`-threshold escalation path, an apparent self-contradiction with the worked example — spec reworded to state both mechanisms explicitly and how they compose.
  - `[medium]` `[bad_spec]` Only segment 2 was named for `_sanitize_id_segment` treatment in §1/§2's prose, not the full `<pkg>@<ver>` tail (vuln.py's actual precedent sanitizes every segment) — spec corrected.
  - `[low]` `[bad_spec]` The literal token `unknown` colliding with a legacy setuptools `"UNKNOWN"` license-metadata artifact was left unacknowledged — spec now states this collision is semantically intentional, not a defect.

### 2026-07-18 — Review pass 2
Fresh Blind Hunter + Edge Case Hunter pass against the pass-1-corrected decision record. Both reviewers independently verified citations against live source; I additionally re-verified the highest-stakes claims myself (grep for the cited function name, an actual Python regex test, a direct read of `epics.md:460`, `report-schema.json:87`, `interfaces.py:349-383`, and `waiver.py`'s `bypass_blocking`/`emit_bypass_stanza`) before accepting them. 9 findings root-caused in this spec's pass-1 amendment (a misattributed ownership call, an unresearched `--bypass` question, a never-pinned unit, an incomplete call-site survey, a naming collision I never checked, and a KEEP-instruction gap that let real pass-1 content get dropped); 10 findings were pass-2-draft-original defects, most notably a fabricated citation and an empirically false mechanism claim, bundled into the same amendment rather than processed separately.
- intent_gap: 0
- bad_spec: 9: (high 3, medium 5, low 1)
- patch: 10: (high 3, medium 1, low 6)
- defer: 2
- reject: 0
- addressed_findings:
  - `[high]` `[bad_spec]` Pass 1's draft correctly extended `ComplianceReport.__post_init__`'s axis-coherence cross-check for the two new families; pass 2's rewrite silently dropped that content, and never added the schema-level `allOf` mirror either — spec now explicitly instructs restoring + extending both.
  - `[high]` `[bad_spec]` `lag`'s unit (days vs. releases-behind) was never pinned despite an entire precedence rule depending on it — spec now pins "releases behind latest," distinguished from the separate day-based `max_age_ok` staleness field.
  - `[high]` `[bad_spec]` The implementation map never named `extract/pyproject.py`/`extract/_identity.py` as real production sites constructing `Component(...)` directly (verified via grep) — spec now requires naming every real construction site, not just `inventory.py`/`conftest.py`.
  - `[medium]` `[bad_spec]` This spec's own pass-1 Fix 7 misattributed the "uncovered" finding's ownership to Story 6.5; verified the actual precedent code (`interfaces.py:349-383`) is unconditional `DefaultPolicy` composition logic Story 6.1 must extend, not Story 6.5's gated-escalation layer — corrected.
  - `[medium]` `[bad_spec]` `SuppressedFinding.source` collides in meaning with the pre-existing `VulnData.source` (free-text provenance) and the new `license`/`currency` section-level `{source,...}` provenance shape — spec now renames the discriminator to `origin`.
  - `[medium]` `[bad_spec]` `_sanitize_id_segment`'s own empty-string-degrades-to-`"unspecified"` fallback (verified in its docstring/body) was never reconciled against the intentional `unknown` token — spec now requires the producer to resolve to `unknown` before sanitizing, never relying on the fallback.
  - `[medium]` `[bad_spec]` Whether `--bypass` needs its own `SuppressedFinding` source value was never researched — verified `bypass_blocking`/`emit_bypass_stanza` (`waiver.py`) is a distinct, pre-existing, transient whole-run mechanism, not a persistent per-finding suppression source — spec now states explicitly why it's out of scope.
  - `[low]` `[bad_spec]` No `license` sub-object JSON schema draft existed alongside the `currency` one — spec now requires both.
  - `[low]` `[bad_spec]` The `!python-runtime` sentinel's collision-freedom against a hypothetical garbage-extracted (not real-registry) component name was unaddressed — spec now requires one acknowledging sentence in Residual Risks.
  - `[defer]` The inherited `@`-escaping gap (`_sanitize_id_segment` never escapes `@`, so a `RAW_MALFORMED` component name containing a literal `@` could break `&lt;pkg&gt;@&lt;ver&gt;` tail injectivity) is pre-existing across the shipped `vuln:` family too, not introduced by this story — filed to `deferred-work.md`, not blocking 6.1.
  - `[defer]` The family regex `[^:\n]+` only excludes literal `\n`, not the full line-boundary character set `_sanitize_id_segment` escapes (CR/VT/FF/NEL/LS/PS) — inherited unchanged from the three shipped families, not introduced by this story — filed to `deferred-work.md`, not blocking 6.1.

### 2026-07-18 — Review pass 3
Fresh Blind Hunter + Edge Case Hunter pass against the pass-2-corrected decision record — a genuine fourth read, not assuming pass-2's extensive self-audit was trustworthy just because it claimed rigor. Both reviewers independently verified citations against live source; I additionally re-verified the highest-stakes claims myself (grep for the cited quote's real file, a direct read of `models.py:371-441`'s actual `__post_init__` body, the `$defs` block's real closing brace, `report-schema.json`'s `vuln_data` if/then null-narrowing pattern, and — most importantly — traced `interfaces.py:390-421`'s `axis_by_id` dedup logic by hand against the record's own proposed code sketch) before accepting them. All 19 findings this pass were `patch`-category — no fabricated citations, no empirically false claims (a marked improvement over pass 2) — so no spec amendment or revert was needed; all 19 were auto-fixed directly on the artifact in this pass.
- intent_gap: 0
- bad_spec: 0
- patch: 19: (high 3, medium 8, low 8)
- defer: 0
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` **Genuine correctness bug, not just a citation issue:** §4's proposed `DefaultPolicy` extension used the bare token `"uncovered"` for both new axis checks, identical to the existing `hygiene_covered` block's own token — verified `interfaces.py:390-421`'s `axis_by_id` dedup keys purely on the constructed `finding_id` string, so a component failing hygiene+license+currency coverage simultaneously would collapse all three into one `Finding`, silently losing two axes' worth of information. Fixed by axis-qualifying the two new tokens to `uncovered-license`/`uncovered-currency`.
  - `[high]` `[patch]` Two `allOf`/`if`/`then` coherence clauses in §5.4(b) were vacuously satisfiable — JSON Schema's `properties` keyword is a no-op on an absent key, so a finding omitting the `license`/`currency` sub-object entirely would still validate. Added `"required": ["license"]`/`"required": ["currency"]` inside each `then` branch.
  - `[high]` `[patch]` The currency id-reason segment was left schema-open (`[^:\n]+`) despite being a genuinely closed 3-value set with a full precedence rule already pinned — a mistyped/novel reason token would silently bypass every §5.4(b)/(c) coherence check. Closed the regex to `(eol|over-lag|unknown)` in the Python family tuple and the schema `anyOf` pattern; corrected the incorrect analogy to hygiene's genuinely-open DEP-code vocabulary.
  - `[medium]` `[patch]` §5.3's `currency` sub-object was missing the `tier` field that §4's own prose (and this same section's prose) asserted it carried — a self-contradiction. Re-added `tier` to the JSON draft.
  - `[medium]` `[patch]` §5.4(b)'s currency id-reason↔verdict mapping was left as prose only, unlike every other coherence clause in the document, which are fully drafted as JSON. Drafted all three `allOf`/`if`/`then` triples explicitly.
  - `[medium]` `[patch]` §5.4(c)'s "require latest/lag/eol_date" clause only checked key presence, not non-null value — an explicit `null` would still validate. Narrowed the field types to exclude `null` in the `then` branch, mirroring the real `vuln_data.max_age_ok` if/then precedent (`report-schema.json:90-98`).
  - `[medium]` `[patch]` §3 misattributed a "Story 3.1 landed the policy stage module" quote to `config.py`'s docstring; verified the quote is actually in `interfaces.py:13`. Corrected the file attribution.
  - `[medium]` `[patch]` §5.5 claimed a `suppressions[]`↔`findings[]` cross-check would "mirror the rigor `StatusDriver`'s existing cross-check already gets" — verified no such runtime check exists anywhere in `__post_init__` today (only documented in a class docstring, never enforced). Corrected the claim to state this is new rigor, not a mirrored precedent, and added the concrete code sketch for both the cross-check and the `suppressions[]` uniqueness invariant (previously only documented prose).
  - `[medium]` `[patch]` §2's precedence rule only stated the 2-way `eol`-beats-`over-lag` case, while §5.4(b) referenced a "pinned" 3-way order that was never actually stated. Made the full 3-way order (`eol` > `over-lag` > `unknown`) explicit in §2.
  - `[medium]` `[patch]` The Provenance note's raw-finding-count arithmetic (21 + 19 = 40) didn't reconcile with the stated "35 numbered fixes," with no explanation offered. Reworded to clarify these are two different measurements (raw findings vs. deduplicated fix count), not a sum that should match.
  - `[medium]` `[patch]` The `!python-runtime` sentinel's residual risk was mislabeled "inherited" — verified the sentinel is new to this record, not carried over from shipped code. Corrected the attribution.
  - `[low]` `[patch]` §4's "all 11 [reducer] fields computed via set/min/max/AND reducers" overgeneralized — verified `name`/`purl` actually use a distinct "agree-else-canonicalize" pattern (`inventory.py:322-325`). Corrected the characterization.
  - `[low]` `[patch]` §5.4's header claimed "two different coherence concerns" but listed three lettered clauses with no reconciliation. Reworded to name the grouping explicitly.
  - `[low]` `[patch]` An inline citation said "docstring, line 7" for a quote spanning `models.py:7-8`, inconsistent with the same item's own more precise Evidence-section citation two paragraphs later. Corrected to "lines 7-8."
  - `[low]` `[patch]` The `$defs` block span was cited as `report-schema.json:263-362`; verified the block's own closing brace is actually at line 363 (362 closes only the nested `axisCoverage` sub-definition). Corrected both occurrences.
  - `[low]` `[patch]` The `vuln.py` citation range (`699-730`) excluded line 745, which the same paragraph goes on to cite. Widened to the function's full span, `699-762`.
  - `[low]` `[patch]` `LicenseVerdict`/`CurrencyVerdict` were introduced with no acknowledgment of the codebase's existing, meta-test-guarded "verdict" concept (`verdict.py`'s composed `Status` lattice). Added a disambiguating naming note.
  - `[low]` `[patch]` The `--bypass` mechanism's correct exclusion from `SuppressedFinding`'s scope left an unstated consumer-facing gap: a reader of `suppressions[]` alone would not know bypass-driven findings exist. Added an explicit statement of what `suppressions[]` does and does not cover.
  - `[low]` `[patch]` §6's worked-examples table header still cited the old open currency regex (`currency:[^:\n]+:.+@.+`) after §2's closure fix; the hand-off section's schema-pattern citation had the same staleness. Updated both to the closed-vocabulary pattern.
  - `[low]` `[patch]` "How Story 6.1 applies this" item 2 also carried the stale open-currency-regex pattern in its `$defs.finding.id.anyOf` guidance. Updated to match §2's closure.

## Auto Run Result

Status: done

**Change:** Authored the Story 6.10 design-spike decision record —
`_bmad-output/projects/pyforge-warden/planning-artifacts/finding-id-verdict-encoding-decision.md`
(1068 lines, committed) — pinning the four shapes Story 6.1's schema
amendment depends on: (1) the `license:`/`currency:` finding-ID grammars
(closed 3-value reason vocabulary for currency; a collision-proof
`!python-runtime` sentinel for the runtime-currency field; sanitization
confirmed load-bearing for SPDX's `DocumentRef:LicenseRef` colon syntax);
(2) the `LicenseVerdict`/`CurrencyVerdict` closed `StrEnum` typed encoding,
disambiguated from `verdict.py`'s unrelated composed `Status` lattice; (3)
the `SuppressedFinding` rung-discriminator (`origin: baseline|waiver`,
renamed from a colliding `source`) with its `report-schema.json`
placement, four coherence clauses, and a concrete uniqueness/cross-check
code sketch; (4) the Gap-B merge/fold table for the two new `Component`
fields (`license_covered`/`currency_covered`), including a real
implementation pitfall in `_fold_bare`'s `dataclasses.replace()` call and
a real production `Component(...)` construction-site survey
(`extract/_identity.py`, `extract/pyproject.py`). This is a pure
decision/documentation deliverable — zero production `src/pyforge/warden/`
or `data/` changes, verified by `git status` and an unchanged test count
at every pass.

**Files changed:** one new git-tracked file —
`_bmad-output/projects/pyforge-warden/planning-artifacts/finding-id-verdict-encoding-decision.md`
— the sole deliverable this story produces.

**Review findings breakdown (3 full adversarial review cycles, Blind
Hunter + Edge Case Hunter each pass, this session's own independent
verification layered on top of every pass):**
- **Pass 1** — 21 raw findings (9 `bad_spec`, 12 `patch`). Root-caused in
  gaps in this spec's own original Design Notes: an uncollision-proofed
  `runtime-python` literal, a factually wrong "SPDX never contains colons"
  claim, a missing FR34 `latest` field, an F1-vs-F3 citation mislabel, an
  unjustified nullable-field deviation from `WaiverNotice`. Triggered a
  `bad_spec` loopback — spec amended, decision record reverted and
  re-derived.
- **Pass 2** — 19 more raw findings (9 `bad_spec`, 10 `patch`) against the
  corrected draft — including a **fabricated citation** (`_finding_from_group`,
  a function that does not exist — confirmed via `grep -rn` returning zero
  hits) and an **empirically false claim** that an unescaped colon breaks
  regex `.fullmatch` (disproven by directly executing the regex). Also
  caught a regression: pass 1's correct axis-coherence content was
  silently dropped by pass 2's rewrite. Triggered a second `bad_spec`
  loopback with an even more explicit, pre-verified amendment.
- **Pass 3** — 19 more raw findings, this time **entirely `patch`-category**
  — no fabrications, no false claims, only precision/completeness gaps.
  Most significant: a **real, confirmed correctness bug** — the proposed
  `DefaultPolicy` extension reused the bare token `"uncovered"` across
  hygiene/license/currency axes, which `interfaces.py`'s `finding_id`-keyed
  `axis_by_id` dedup would silently collapse into one `Finding` when a
  component fails multiple axes' coverage simultaneously (traced and
  confirmed by hand against the real dedup loop before fixing). Also found:
  two vacuously-satisfiable JSON-Schema coherence clauses, an
  un-closed currency reason vocabulary, a missing `tier` field
  contradicting the document's own prose, and several citation-precision
  slips. All 19 were patched directly in place (no further loopback needed —
  none required reverting the spec).
- **Deferred (2):** two pre-existing, inherited gaps surfaced incidentally
  (`_sanitize_id_segment` never escaping `@`; the shipped family regexes'
  `[^:\n]+` not covering the full line-boundary character set) — filed to
  `deferred-work.md`, not blocking Story 6.1, not introduced by this story.
- **Rejected:** 0 across all three passes — every finding raised by either
  reviewer was independently verified as real before being triaged.

**Verification performed:** `pixi run --frozen -e pyforge-warden
pyforge-warden-test` → **1227 passed**, identical at every pass (a pure
documentation change cannot regress tests). `git status` confirmed a
single-file diff at every checkpoint. Every load-bearing citation in the
final draft was independently re-verified this session via fresh
`Read`/`grep`/Python execution against the live source
(`models.py`, `interfaces.py`, `inventory.py`, `waiver.py`, `config.py`,
`vuln.py`, `hygiene.py`, `report.py`, `cli.py`, `extract/_identity.py`,
`extract/pyproject.py`, `data/report-schema.json`,
`tests/conftest.py`) and the planning docs (`architecture.md`, `epics.md`,
`prd.md`) — not trusted from any prior draft or subagent self-report. All
8 hand-authored JSON snippets were validated as syntactically correct.

**Residual risks (recorded in the decision record's own § Residual
Risks):** `EffectiveConfig.license_policy`/`.currency_policy` land outside
Story 6.1's literal file list, deferred to Story 6.2/6.3 by precedent;
`baseline.py`'s own entry-validation design stays Story 6.8's job; the
`!python-runtime` sentinel remains theoretically collidable only against
hypothetical `RAW_MALFORMED` garbage data, never a real registry entry;
`--bypass`-driven suppressions are intentionally invisible to
`suppressions[]` (a documented scope boundary, not a gap); two pre-existing
grammar gaps (`@`-escaping, line-boundary character coverage) are filed to
`deferred-work.md`. `followup_review_recommended: true` — given the depth
of this story's revision history (a fabricated citation and a real
correctness bug were each caught only on a second/third independent
pass), an independent follow-up review before Story 6.1 consumes this
record is warranted despite pass 3 finding no further `bad_spec`-level
issues.
