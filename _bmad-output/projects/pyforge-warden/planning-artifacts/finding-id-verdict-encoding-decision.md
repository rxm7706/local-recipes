---
title: 'Finding-ID families, verdict encoding, rung-discriminator & fold semantics — decision record (Story 6.10 spike)'
type: 'decision-record'
status: 'accepted'
created: '2026-07-18'
story: '6.10'
gates: ['6.1']
does_not_gate: ['6.2', '6.3', '6.4', '6.5', '6.6', '6.7', '6.8', '6.9']
downstream_owners: ['6.1', '6.2', '6.3', '6.5', '6.8']
evidence_env: 'N/A -- no external tool to probe. Every recommendation is grounded in cited shipped source (models.py / interfaces.py / waiver.py / config.py / inventory.py / report.py / report-schema.json / vuln.py / tests/conftest.py), re-read or re-grepped directly this session -- see "Why no empirical evidence table" below.'
---

# Finding-ID families, verdict encoding, rung-discriminator & fold semantics — decision record

This is the tracked output of the **Story 6.10 spike**. It resolves the four
open design questions Story 6.1's own scope list depends on but does not
itself answer (epics.md's Story 6.1 AC): the `license:`/`currency:`
finding-ID grammars, the typed verdict encoding policy/waiver/baseline
tables key on, the suppression rung-discriminator shape (baseline vs
waiver, echoed in the JSON contract for the first time — today's
`WaiverNotice` is echoed only in `render_text`, never JSON), and the Gap-B
merge/fold semantics for the new `Component` fields license/currency
coverage-tracking requires. It **gates Story 6.1 only** — 6.1 is itself the
transitive HARD gate for every other 6.x producer story (6.2–6.9), so this
record's `does_not_gate` list names all eight of them explicitly to make
clear they are gated *through* 6.1, never directly by this spike (mirrors
the Story 1.4 precedent's "gates 1.5+2.4, not 1.3" disposition line).
`downstream_owners` additionally names every story whose own AC text this
record's sections assign explicit ownership to (6.1/6.2/6.3/6.5/6.8 — see
each section's "Owner" line).

Every recommendation below extends an already-shipped, already-tested
pattern injectively: `models.py`'s three finding-ID family regexes,
`config.py`'s `SeverityTier`-keyed policy-table shape, `waiver.py`'s
`WaiverNotice`/`apply_waivers` shape, and `inventory.py`'s Gap-B
`merge_components`/`_merge_group`/`_fold_bare` mechanism.

**Provenance note.** This is a fourth-pass re-derivation. Three prior drafts
of this record were each reviewed and found to have defects rooted partly
in gaps in the spec's original design and partly in the drafts' own
execution: pass 1 drew 21 raw review findings (9 `bad_spec` + 12 `patch`);
pass 2's corrected draft drew 19 more raw findings (9 `bad_spec` + 10
`patch`) — including a fabricated citation (a function name,
`_finding_from_group`, that does not exist anywhere in the codebase) and an
empirically false claim about regex behavior; pass 3's corrected draft drew
19 more raw findings, this time entirely `patch`-category (precision/
completeness gaps, no fabrications) — most notably a real axis-collision
bug in the "uncovered" finding token (§ 4, fixed below) and two vacuous
JSON-Schema coherence clauses (§ 5.4). 40 raw findings from passes 1–2 were
consolidated into 35 numbered fixes after deduplicating overlap between the
two reviewers within each pass (the "35" is a fix count, not a raw-finding
sum — the two numbers measure different things and were never meant to be
equal). Pass 3's 19 findings are folded into this draft directly, patched
in place rather than numbered, since none required reverting the spec.
Every citation in this draft — every file:line reference, every function
name, every regex claim — was independently re-verified this session via a
fresh `Read`/`grep`/Python execution, not transcribed from any prior draft.
Where a prior draft's cited line number had drifted from the live source,
the number below is the one this session actually observed.

## Why no empirical evidence table (unlike Story 1.4)

Unlike Story 1.4's OSV-DB spike, this spike has no external tool to probe —
every shape here is derived by direct, cited analogy to already-shipped,
already-tested code (`models.py`'s regex family, `config.py`'s policy-table
pattern, `inventory.py`'s merge/fold rows, `report-schema.json`'s `$defs`
style). Each numbered section's "Evidence" is that citation — a file:line
reference verified this session — not a measurement.

---

## 1. License finding-ID grammar

**Recommendation:** `license:<spdx-expression-or-"unknown">:<pkg>@<ver>` —
regex `license:[^:\n]+:.+@.+`, matching the shipped `vuln:` shape exactly
(same `<pkg>@<ver>` tail). Segment 2 is the SPDX expression itself (or the
literal token `unknown` when unresolvable) — the injective "why," directly
analogous to `vuln:`'s advisory-id segment. A finding is emitted **only**
for `denied`/`unknown` verdicts — never for `allowed` (matches the
"findings exist only for problems" invariant already true of the hygiene
and vulnerability axes; the schema enforces this — § 5.4 below).

`_sanitize_id_segment` (`interfaces.py:119–138`) is **load-bearing, not
merely defensive**, for this family, and it applies to **every** segment
the producer supplies — segment 2 (the SPDX expression) AND the
`<pkg>@<ver>` tail — mirroring `vuln.py`'s own precedent (§ evidence
below), not just segment 2. This matters because SPDX expressions
legitimately embed a literal `:`: the SPDX License List Matching
Guidelines' `DocumentRef-<idstring>:LicenseRef-<idstring>` construct
(custom/vendored license references) is standard SPDX syntax, not an edge
case. Without sanitization, a component whose SPDX expression is
`DocumentRef-vendor:LicenseRef-my-custom-1.0` would inject an extra
colon-delimited segment into the id, breaking the two-segment structure the
grammar depends on for stable, unambiguous round-tripping.

**On the "does the colon break matching" question (re-verified this
session, see § evidence):** an *unescaped* colon does **not** break
`.fullmatch` — Python's regex engine backtracks and still finds a valid
split. The real risk sanitization closes is **injectivity/stability**, not
matching: two different underlying SPDX expressions could stringify to
ambiguous or unstable ids, and any consumer that manually `.split(":")`s an
id instead of treating it as an opaque string would misparse it. Waiver
matching (`waiver.py`'s dict lookup keyed on the *whole* `finding_id`
string) is **not** such a consumer and is unaffected either way — this
draft does not claim it is.

The version-tail convention mirrors `vuln.py`'s verified precedent exactly
(§ evidence): `_sanitize_id_segment(component.version) if component.version
else "unspecified"` — the fallback decision is made **before** calling
sanitize, not by relying on `_sanitize_id_segment`'s own internal
empty-string fallback (see § evidence's discussion of
`interfaces.py:138`). A component with no resolved version still gets a
well-formed finding id using the literal `unspecified` tail segment.

**The `unknown` token intentionally collides with legacy `"UNKNOWN"`
license metadata.** setuptools has historically emitted the literal string
`"UNKNOWN"` as a license placeholder when no license metadata was
supplied. A component whose resolved SPDX expression is exactly that
legacy artifact and a component whose license genuinely could not be
resolved both denote "no reliable SPDX identifier available" — the
collision onto the same `unknown` token is semantically correct, not a
defect.

**Guard against an `unknown`/`unspecified` collision on the *same*
segment.** `_sanitize_id_segment` (`interfaces.py:119–138`) has its own
internal fallback at its final line: `return escaped if escaped else
"unspecified"` (`interfaces.py:138` — re-verified this session via a fresh
`grep -n`; this is the current line, corrected from an earlier draft's
stale citation). An empty string degrades to the literal token
`unspecified`. This is a **different** meaning from the intentional
`unknown` token above and must never collide on the same segment: the
license producer must resolve to the literal token `unknown` **first**
(before ever calling `_sanitize_id_segment` on the expression segment),
the same way `vuln.py`'s version-segment logic decides its fallback before
sanitizing rather than depending on sanitize's own fallback. This keeps
`unknown` ("we genuinely don't know, by design") and `unspecified` (which
would only appear as a symptom of a producer bug) from ever meaning the
same thing on the same segment.

**Evidence:** `interfaces.py:119–138` (`_sanitize_id_segment`, re-read this
session — escapes `%` first, then every `str.splitlines()` line-boundary
character, then `:`; empty string falls back to `"unspecified"` at line
138). `vuln.py:699–762` (`_findings_for_package`, the full function span
— widened from an earlier draft's 699–730, which excluded line 745 the
same paragraph goes on to cite — re-verified this session via
`grep -rn "_finding_from_group"` returning **zero** hits and a
fresh read of the function; the real precedent function name is
`_findings_for_package`, not any fabricated name): line 725
`name_segment = _sanitize_id_segment(pkg_name)` (unconditional), lines
726–730 `version_segment = (_sanitize_id_segment(pkg_version) if
isinstance(pkg_version, str) and pkg_version else "unspecified")`
(conditional, decided before sanitizing), and line 745
`f"vuln:{_sanitize_id_segment(advisory_id)}:{name_segment}@{version_segment}"`
— every producer-supplied segment passes through sanitize or an explicit
pre-sanitize fallback; none is used raw. The `.fullmatch`-doesn't-break
claim was verified this session by direct execution:
`python3 -c "import re; print(re.compile(r'license:[^:\n]+:.+@.+').fullmatch('license:DocumentRef-vendor:LicenseRef-my-custom-1.0:acme-widget@2.0.0'))"`
returns a **successful match** (backtracking finds a valid split) — the
regex engine tolerates the unescaped colon; the risk is injectivity, not
matching, and this draft states it that way. `models.py:1–19` (module
docstring's finding-ID scheme + `_FINDING_ID_FAMILIES` at `models.py:46–50`
— the shipped three-family precedent this section extends with a fourth
entry). **Owner:** Story 6.1 (`models.py` — widen `_FINDING_ID_FAMILIES`;
`report-schema.json` — widen `$defs.finding.id.anyOf`, § 5.2).

## 2. Currency finding-ID grammar

**Recommendation:** `currency:<reason>:<subject>@<ver>` — regex
`currency:(eol|over-lag|unknown):.+@.+`. **Unlike `hygiene:`'s DEP-code
segment (an open, growing producer-code vocabulary the id regex
deliberately does not enumerate — confirmed at `hygiene.py:3–4,137–151`),
`<reason>` is a genuinely closed, exactly-3-value set with no stated growth
path — the same closed-enum posture as `LicenseVerdict`/`CurrencyVerdict`
themselves (§ 3).** An earlier draft analogized `<reason>` to hygiene's open
DEP-code vocabulary and left the regex generic (`[^:\n]+`); that analogy was
wrong for this segment specifically, and the regex is now closed to match
the actual 3-value set, catching a mistyped/novel reason token at
construction time instead of letting it silently bypass every § 5.4(b)
coherence clause. A finding is emitted only for `eol`/`over-lag`/`unknown`
— never for a clean `supported`-with-no-lag component.

**Precedence, fully pinned as a 3-way total order: `eol` > `over-lag` >
`unknown`.** When a component is simultaneously `eol` and beyond
`--max-lag`, the reason token is `eol` — the more severe/terminal
classification — with the numeric `lag` field still populated on the
finding for transparency even though `eol` wins the reason-token slot.
`unknown` is the floor of the order: it only applies when no tier data
resolves at all (§ 2's ladder-miss case), so it can never simultaneously
compete with a resolved `eol`/`over-lag` classification — the 2-way
`eol`-beats-`over-lag` rule and `unknown`'s floor position together fully
determine the 3-way order (an earlier draft's § 5.4(b) cited a "pinned"
3-way order this section only implied; it is now stated explicitly here).

**`<subject>` is `<pkg>` for a component.** For the FR34 first-class
Python-runtime-currency field, the id's `<subject>` segment is **not** the
bare literal `runtime-python` — a real PyPI/conda package could
legitimately be named `runtime-python` (PEP 508/PEP 503's package-name
grammar, `[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?`, permits it), producing
an indistinguishable id collision between the interpreter's own currency
finding and a real dependency's. Use the reserved sentinel
`!python-runtime` instead — `!` is not a legal character in any PyPI or
conda package name, so this token is structurally uncollidable with any
real component subject. Both shapes still fold into the same `X@Y` tail
the regex expects (e.g. `currency:eol:!python-runtime@3.8.18`). This
sentinel is distinct from the report *section's* Python-runtime currency
field name, `runtime_python` (underscore, per epics.md's Story 6.3 AC
text, "runtime_python currency is a first-class field") — the two live at
different levels (a finding-id token vs. a report-section field name) and
must not be conflated.

**Version-tail + `unknown`/`unspecified` guards** are identical to § 1's —
see there for the full statement; they apply here unchanged (`<ver>`
defaults to `unspecified` before sanitizing when absent; the `unknown`
reason token must be resolved before any call to `_sanitize_id_segment` on
that segment).

**Evidence:** `hygiene.py:3–4,137–151` (the `hygiene:<DEP-code>:<subject>`
open-vocabulary convention this section's `<subject>` tail shape borrows,
while explicitly NOT borrowing its open-regex posture for `<reason>` — see
the closed-3-value correction above). PEP 508/PEP 503
package-name grammar (external spec text, not a repo citation — the
`!`-exclusion claim is a property of that published grammar, independently
checkable). `vuln.py:699–762` (the version-tail + sanitize-order
precedent, same as § 1). **Owner:** Story 6.1 (`models.py` —
`_FINDING_ID_FAMILIES`; `report-schema.json` — `$defs.finding.id.anyOf`).
Story 6.3 (the currency producer — chooses `eol` over `over-lag` at
finding-construction time per this section's precedence rule, and uses the
`!python-runtime` sentinel for the runtime finding).

## 3. Typed verdict encoding

**Recommendation:** two new CLOSED `StrEnum`s in `models.py`, co-located
with `Status`/`CveMatchLevel`/`WithholdReason` but **not** added to the
sanctioned-growable list (`models.py`'s own docstring, lines 7–8: "Growable-
enum policy: ONLY `CveMatchLevel` and `WithholdReason` may widen
(additively) later" — re-verified this session; FR32/FR34 each pin exactly
3 values with no stated growth path, so these two enums are closed,
additively-widenable-only-via-schema-bump exactly like `Status` itself).
**Naming note — distinct from `verdict.py`'s "verdict."** This codebase
already uses "verdict" for a heavily-loaded, meta-test-guarded concept: the
composed 7-rung `Status` lattice, sole-owned by `verdict.py` and enforced by
`tests/meta/test_verdict_sole_ownership.py`. `LicenseVerdict`/
`CurrencyVerdict` name a *different*, narrower thing — a per-component,
per-axis classification (epics.md's own vocabulary: "an honest SPDX license
verdict," "tiered, age-honest currency verdicts") that feeds INTO the
composed verdict via `verdict.py`'s rung composition, not a second verdict
lattice. The name is FR32/FR34's own term, kept for traceability, but a
future implementer skimming for "the verdict" should not conflate the two —
`LicenseVerdict`/`CurrencyVerdict` are `Finding`-level inputs; `Status` is
the one composed, sole-owned output:

```python
class LicenseVerdict(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    UNKNOWN = "unknown"

class CurrencyVerdict(StrEnum):
    SUPPORTED = "supported"
    EOL = "eol"
    UNKNOWN = "unknown"
```

The **closed verdict enum** is the only thing free-text policy/waiver/
baseline **matching** may key on — this closes the smuggle path where a
free-text `indeterminate:<reason>:...` token could otherwise be used as a
de facto policy key (this closes adversarial-review finding **F1**, per
`architecture.md:134`, re-verified this session: "...schema-validated
fields, never free-text `indeterminate:` reason tokens — policy tables and
baseline/waiver matching key ONLY on these; closes adversarial F1" — F1,
not F3; F3 is the unrelated post-verdict `actuation` section,
`architecture.md:137`).

A **numeric threshold comparison** (`lag` vs `--max-lag`) is a second,
additive escalation input Story 6.5 evaluates *alongside* the
verdict-keyed table lookup — not a competing free-text mechanism. Both
together decide the final rung for a `CurrencyVerdict.SUPPORTED` finding:
the verdict-table lookup handles `eol`/`unknown` unconditionally, while a
`supported` verdict whose `lag` exceeds the configured `--max-lag`
threshold is a *second*, additive check Story 6.5's escalation mapping
applies on top. `CurrencyVerdict` itself stays exactly `supported`/`eol`/
`unknown` (3 values) — `over-lag` is never a 4th enum member; it lives only
as an id-grammar reason token (§ 2) whose corresponding verdict is
`supported` (§ 5.4's coherence clause makes this the schema-enforced
mapping).

**`lag`'s unit is releases-behind-latest (an integer count), not
days/calendar-time.** `--max-lag <n>` reads naturally as a release-count
threshold, and a separate, already-named concept — `max_age_ok`
(NFR-S9's bundled-data staleness field, `models.py:214–228`,
`report-schema.json:83–103`) — already owns the day/calendar-time axis;
`lag` would be redundant with it if also time-based. When a verdict
derives from a date-based ladder tier (endoflife.date), Story 6.3's
producer computes an equivalent release-count approximation for `lag`;
when it derives from a release-position tier (N/N-1 channel data), `lag`
is exact.

**`EffectiveConfig.license_policy`/`.currency_policy` are Story 6.2/6.3's
job, not 6.1's** (a scope clarification, not a fix — see the hand-off
section below for the reasoning): they will mirror `vuln_severity_policy`'s
shape — an `@property` (not a callable method — verified this session at
`config.py:245–263`), returning `dict[LicenseVerdict, Status]`/
`dict[CurrencyVerdict, Status]` — but `config.py` is not in Story 6.1's
literal coordinated-update-set (epics.md:460), and the precedent itself
(`interfaces.py`'s own module docstring, `interfaces.py:13` — re-verified
this session; the quote is NOT in `config.py`, an earlier draft misattributed
it: "the policy stage module (`config.py`'s `EffectiveConfig`/...)") shows
that adding a policy-table property to `EffectiveConfig` is
historically a later, axis-specific story's job, not the schema-amendment
story's. 6.1 defines the two new enum *types* (needed for
`report-schema.json`'s `license`/`currency` sub-object `verdict` enums);
6.2/6.3 add the config properties that consume them, exactly as FR33/FR35
and epics.md's Story 6.2/6.3 ACs already say ("the flags parse into the
FR30 ConfigLoader tables and `config.py` flips the ... axis's `gating`
bool").

**Evidence:** `config.py:245–263` (`vuln_severity_policy` — re-read this
session: `@property` decorator at line 245, `def` at 246, returning
`dict[SeverityTier, Status]`, confirming it is a property, not a
method). `models.py:7–8` (growable-enum policy, re-read this session).
`architecture.md:134` (re-read this session — confirms F1, not F3).
`architecture.md:137` (F3 — confirmed unrelated, the `actuation` section).
`epic-6-context.md` § Technical Decisions ("NFR-S9 ... default max-age 180
days"). **Owner:** Story 6.1 (`models.py` — the two closed `StrEnum`
definitions only). Story 6.2/6.3 (`config.py` — the `license_policy`/
`currency_policy` properties + `--allow-licenses`/`--deny-licenses`/
`--max-lag`/`--require-lts`/`--fail-on-eol` flag parsing). Story 6.5 (the
composed escalation mapping — both inputs, verdict-table lookup AND the
numeric `lag`-threshold check, together).

## 4. New `Component` fields + Gap-B fold table

**Recommendation:** exactly two new boolean fields, mirroring
`hygiene_covered`'s binary "was this axis even attempted" semantic — **not**
`vuln_matchable`'s match-strength semantic. Re-verified this session:
`vuln_matchable`'s actual formula (`inventory.py:342–345`,
`_merge_group_pypi_identity`-derived) is `all(component.vuln_matchable for
component in group) and pypi_identity is not None` — an AND *plus* an
identity-resolution gate, not a pure AND like `hygiene_covered`
(`inventory.py:368`: `hygiene_covered=all(component.hygiene_covered for
component in group)`). License/currency resolution has no multi-tier
confidence, only pre-build-metadata-available-or-not, so a plain AND is
correct for these two new fields specifically.

| New field | Type | `_merge_group` rule | `_fold_bare` rule |
|---|---|---|---|
| `license_covered` | `bool` | AND (all records in the same-identity group must be covered) | AND (both `concrete` and the bare record must be covered) |
| `currency_covered` | `bool` | AND | AND |

Both rules match the existing `hygiene_covered` AND-row verbatim
(conservative C0: merging/folding never upgrades coverage confidence).

**Field-count accounting (stated once).** `Component`
(`inventory.py:69–91`, re-verified this session) has 13 fields today: name,
version, ecosystem, pypi_identity, identity_source, mapping_confidence,
cve_match_level, extraction_mode, purl, provenance, hygiene_covered,
vuln_matchable, indeterminate_reason. Of these, **11 carry a real
`_merge_group` reducer** (name, purl, cve_match_level, extraction_mode,
pypi_identity, identity_source, mapping_confidence, provenance,
hygiene_covered, vuln_matchable, indeterminate_reason — computed via a mix
of set/min/max/AND reducers **and** an "agree-else-canonicalize" pattern:
most use set/min/max/AND, but `name` and `purl` specifically use a third
pattern — keep the raw value if every group member already agrees, else
re-derive/canonicalize (`inventory.py:322–325`, re-verified this session —
not a set/min/max/AND operation), `_merge_group`, `inventory.py:281–371`);
**2
(`ecosystem`, `version`) are identity-invariant pass-throughs** copied from
`group[0]` because they are literally part of the group's identity key
(`identity()`, `inventory.py:145–158`). The two new fields land as
reducer-bearing fields, bringing the reducer count to 13 (15 fields total
after the amendment).

**Implementation pitfall — `_fold_bare` builds via `dataclasses.replace`,
not a full constructor call.** `_fold_bare` (`inventory.py:415–478`,
re-verified this session) constructs its result via `return replace(
concrete, pypi_identity=..., identity_source=..., mapping_confidence=...,
hygiene_covered=..., vuln_matchable=..., extraction_mode=...,
indeterminate_reason=..., provenance=...)` (`inventory.py:468–478`, using
`dataclasses.replace`, imported at `inventory.py:24`) — **not** a full
`Component(...)` constructor call the way `_merge_group` builds its result
(`inventory.py:349–371`, `return Component(name=..., ..., hygiene_covered=...,
vuln_matchable=..., indeterminate_reason=...)`). This asymmetry matters: a
full `Component(...)` call has no defaults (verified — `Component` is a
defaultless frozen dataclass, `inventory.py:69–91`), so omitting a new
field there is a loud `TypeError` at implementation time. `replace()` has
no such guard — `replace()` does not require exhaustive kwargs, so
omitting `license_covered=...`/`currency_covered=...` from `_fold_bare`'s
`replace()` call **silently carries over `concrete`'s existing value**
instead of applying the AND-fold — no missing-arg error, no test failure
unless a test specifically exercises the flip case. **6.1's implementer
MUST include both new fields in `_fold_bare`'s `replace()` kwargs.**
Recommend a dedicated meta-test asserting the folded result differs from
`concrete` in a synthetic AND-should-flip-false fixture (e.g. `concrete`
has `license_covered=True`, the bare record has `license_covered=False`,
and the test asserts the folded result's `license_covered is False`, not
`True` — a test that would pass silently-wrong if the kwarg were omitted
and `replace()`'s default-carry-over behavior went unnoticed).

**Ownership of the "uncovered" finding — Story 6.1, not Story 6.5.**
Re-verified this session: `interfaces.py:375–388` shows the analogous
`hygiene_covered`-driven `indeterminate` finding
(`if not component.hygiene_covered: derived.append((Status.INDETERMINATE,
"uncovered", AXIS_HYGIENE, ...))`) is **unconditional composition logic
inside `DefaultPolicy.evaluate`'s per-component loop**
(`interfaces.py:350–424`) — it runs regardless of any axis-gating
configuration, for every component, every scan. Story 6.5's charter
(epics.md's Story 6.5 AC, "Two-mode policy integration") is specifically
the warn↔policy-violation/indeterminate **escalation mapping** for
**gated** axes — a different, later concern operating on already-derived
verdicts. The correct owner for the "uncovered" finding itself is
**Story 6.1**, which must extend `DefaultPolicy.evaluate`'s per-component
loop with two new parallel blocks:

```python
if not component.license_covered:
    derived.append((
        Status.INDETERMINATE, "uncovered-license", AXIS_LICENSE,
        f"{component.name}: not license-covered -- "
        "license-axis cleanliness cannot be claimed",
    ))
if not component.currency_covered:
    derived.append((
        Status.INDETERMINATE, "uncovered-currency", AXIS_CURRENCY,
        f"{component.name}: not currency-covered -- "
        "currency-axis cleanliness cannot be claimed",
    ))
```

**Critical: the reason token must be axis-qualified (`uncovered-license`/
`uncovered-currency`), not the bare `"uncovered"` the `hygiene_covered`
block uses.** `interfaces.py:390-421`'s `for rung, token, axis, message in
derived:` loop builds `finding_id = f"indeterminate:{token}:{subject}"` and
dedupes on that exact string via `axis_by_id` (`interfaces.py:406-421`):
only the *first* occurrence of a given `finding_id` creates a `Finding` and
registers an axis; every later occurrence of the *same string* silently
skips creating a new `Finding` and reuses the *first* occurrence's axis for
its `StatusDriver`. If both new blocks used the bare token `"uncovered"`
(matching `hygiene_covered`'s own token), a component failing hygiene AND
license AND currency coverage simultaneously would collide all three onto
the identical id `indeterminate:uncovered:<name>` — only one `Finding`
would ever be constructed, and the other two axes' failures would be
silently swallowed, misattributed to whichever axis happened to run first.
Axis-qualifying the two *new* tokens makes all three strings distinct
(`uncovered` stays as-is for `hygiene_covered` — that shipped behavior is
unchanged, out of this spike's scope), closing the collision. Mirror the
existing `hygiene_covered` block (`interfaces.py:375–388`) in every other
respect, alongside it in the same `derived` list. The actual per-component
license/currency verdict data (SPDX expression, tier, `lag`, `eol_date`)
lives on the `Finding`, not on `Component` — `Component` only tracks
assessability (whether the axis was even attempted), matching the existing
`hygiene_covered`/`vuln_matchable` design.

**Real production `Component(...)` construction sites (implementation map,
re-verified this session via `grep -rln "Component(" src/... tests/...`).**
Besides `inventory.py` (`_merge_group`/`_fold_bare`) and
`tests/conftest.py` (`make_component`), the grep also matched `sbom.py`,
`extract/_identity.py`, `extract/pyproject.py`, `tests/unit/test_models.py`,
and `tests/unit/test_vuln.py`. Read individually this session:

- **`sbom.py`** — **false positive.** Its matches are `CdxComponent(` (a
  CycloneDX SBOM library type), a *different* class entirely — `sbom.py`
  does not construct `pyforge.warden.inventory.Component` and needs no
  change.
- **`extract/_identity.py`** (7 sites: lines 171, 228, 253, 268, 292, 481,
  501) and **`extract/pyproject.py`** (3 sites: lines 137, 164, 184) —
  **genuine production construction sites**, confirmed by `from ..inventory
  import (... Component, ...)` in both files. Both need the two new
  fields added or these files fail to construct a `Component` once the
  fields exist (no defaults).
- **`tests/unit/test_models.py`** (`_sample_component()`,
  `test_models.py:125–140`) and **`tests/unit/test_vuln.py`**
  (`test_synthesize_requirements_excludes_leading_dash_name`,
  `test_vuln.py:362–...`) — genuine, test-local full constructions (not
  routed through `make_component`), each also needing the two new fields.

**Evidence:** `inventory.py:69–91` (`Component`), `:145–158` (`identity`),
`:222–278` (`merge_components`), `:281–371` (`_merge_group`), `:342–345`
(`vuln_matchable` formula), `:415–478` (`_fold_bare`), `:24` (`from
dataclasses import dataclass, replace`). `interfaces.py:350–424`
(`DefaultPolicy.evaluate`'s per-component loop), `:375–388`
(`hygiene_covered` block). epics.md's Story 6.5 AC (the escalation-mapping
charter). **Owner:** Story 6.1 (`inventory.py` — the two new `Component`
fields + their `_merge_group`/`_fold_bare` rules, the "exact-N `Component`"
meta-test widening, `extract/_identity.py`/`extract/pyproject.py`'s
construction-site updates, AND `interfaces.py`'s `DefaultPolicy` extension
for the "uncovered" findings). Story 6.5 (the *separate*, later
verdict-table + numeric-lag escalation composition, § 3).

## 5. Suppression rung-discriminator + schema placement

### 5.1 The `SuppressedFinding` shape

**Recommendation:**

```json
{
  "finding_id": "<str>",
  "origin": "baseline | waiver",
  "reason": "<str>",
  "authorized_by": "<str | null>",
  "expires_at": "<str | null>"
}
```

This reuses `WaiverNotice`'s 4 fields (`WaiverNotice`, `waiver.py:133–141`,
re-verified this session — exactly `id`, `reason`, `authorized_by`,
`expires_at`), renaming `id` → `finding_id` (to disambiguate against
`$defs.finding.id`, an unrelated field on a different object), plus a new
closed 2-value discriminator.

**The discriminator field is named `origin`, not `source`.** An earlier
draft used `source`, which collides with two other, semantically different
uses of the same key name in the same document: `VulnData.source`
(`report-schema.json:87`, re-verified this session — a free-text, nullable
data-provenance string) and the section-level `{source, snapshot_at,
max_age_ok}` provenance shape epics.md:460 assigns to the new `license`/
`currency` report *sections* (a different level entirely — per-section
feed provenance, not a per-suppression discriminator). Reusing `source` for
`SuppressedFinding`'s closed 2-value categorical field would create three
unrelated meanings for one key name in the same document — exactly the
ambiguity the `id`→`finding_id` rename above exists to avoid. Renamed to
**`origin`** everywhere: the schema draft, worked examples, prose, and the
hand-off section below all use `origin`, not `source`.

**Why `authorized_by`/`expires_at` are nullable here while `WaiverNotice`
requires both.** `WaiverEntry` (`waiver.py:111–122`) declares
`authorized_by` and `expires_at` as required, non-null fields — a waiver is
individually signed, per-finding risk acceptance. Baseline entries
(Story 6.8, FR39) are accepted in **bulk** via one committed
`.warden-baseline.yaml` file rather than individually signed like a
waiver, so a per-entry `authorized_by` may legitimately be absent for
`origin: "baseline"`. (An earlier draft grounded this in the
`waiver.py:80–83` comment; re-reading that comment this session shows it
is about length-bound *symmetry* between `authorized_by` (200 chars) and
`reason` (1000 chars) — "kept symmetric in KIND ... rather than in VALUE"
— not an explicit statement about per-person accountability. This
paragraph grounds the nullability decision in the field's own name/type/
required-ness and the baseline-vs-waiver acceptance-flow difference
instead.) `expires_at` is nullable for the same bulk-acceptance reason: a
baseline entry may or may not carry an expiry depending on Story 6.8's own
design (out of this spike's scope — see Residual Risks). Full validation-
rule design for `baseline.py` stays out of scope for this spike.

### 5.2 `report-schema.json` placement

New `$defs.suppressedFinding` (additive, alongside the existing
`statusDriver`/`finding`/`axisCoverage` — `report-schema.json:263–363`,
re-verified this session as the current `$defs` block's span; the block
opens at 263 and its own closing brace is at 363, one line past the nested
`axisCoverage` sub-definition's own close at 362):

```json
"suppressedFinding": {
  "type": "object",
  "required": ["finding_id", "origin", "reason"],
  "properties": {
    "finding_id": { "type": "string" },
    "origin": { "enum": ["baseline", "waiver"] },
    "reason": { "type": "string" },
    "authorized_by": { "type": ["string", "null"] },
    "expires_at": { "type": ["string", "null"] }
  }
}
```

New top-level optional `ComplianceReport` field `suppressions:
[SuppressedFinding]`, parallel in shape to `findings` (both are arrays of
`$ref`'d `$defs` objects) — additive: `additionalProperties` stays open
everywhere in this schema (`report-schema.json:5`'s own description states
this explicitly, re-verified this session), so
`test_additive_extra_fields_still_validate`
(`tests/conformance/test_report_schema.py`, confirmed present via `grep`
this session) is unaffected.

### 5.3 License/currency `Finding` sub-object schema drafts

Both a `license` AND a `currency` sub-object must exist on `$defs.finding`
— an earlier draft only had `currency`, despite the coherence clause in
§ 5.4 referencing `Finding.license.verdict`.

```json
"license": {
  "oneOf": [
    { "type": "null" },
    {
      "type": "object",
      "required": ["expression", "verdict"],
      "properties": {
        "expression": { "type": "string" },
        "family": { "type": ["string", "null"] },
        "verdict": { "enum": ["allowed", "denied", "unknown"] }
      }
    }
  ]
}
```

No `source` field on this sub-object — that name is reserved (§ 5.1) and
this level is not where section-level provenance lives.

```json
"currency": {
  "oneOf": [
    { "type": "null" },
    {
      "type": "object",
      "required": ["verdict"],
      "properties": {
        "verdict": { "enum": ["supported", "eol", "unknown"] },
        "latest": { "type": ["string", "null"] },
        "lag": { "type": ["integer", "null"], "minimum": 0 },
        "eol_date": { "type": ["string", "null"] },
        "tier": {
          "enum": ["lts-registry", "endoflife-date", "channel-n-n-1", "unknown", null],
          "description": "Which rung of the FR34 tier ladder resolved this verdict (NFR-S9 provenance)."
        }
      }
    }
  ]
}
```

**`latest` and `tier` were both schema-completeness gaps — an earlier draft
asserted `tier` belonged here (§ 4 above, and this section's own prose two
paragraphs up) but never actually added it to the JSON, a self-contradiction
now closed.** FR34 (`prd.md:565`, re-verified this session: "for every
resolved component ... the tier ladder runs (LTS registry → cached
endoflife.date → N/N-1 from channel data → `unknown`)") establishes the
ladder `tier` names; without a `tier` field the report cannot honestly say
which rung produced a verdict, undermining the NFR-S9 provenance the ladder
exists to support. `latest`/`lag`/`eol_date` are the FR34 per-component
data fields; `tier` is this record's own grounded addition (not a literal
FR34 output-field bullet — FR34's "tiered" language describes the lookup
process) for provenance completeness.

### 5.4 Coherence clauses

Three lettered clauses below, grouped into two concerns: (a) is id-prefix ↔
axis coherence; (b) and (c) are together the id-payload coherence concern
for the two new sub-objects — (c) is a direct extension of (b)'s "the id's
reason token determines what the payload must say" logic, applied to
non-null-ness instead of the `verdict` enum. All three are additive.

**(a) id-prefix ↔ `Finding.axis` coherence (restores content an earlier
draft correctly had and a later draft silently dropped).** The existing
shipped precedent, re-verified this session inside
`ComplianceReport.__post_init__` (`models.py:371–441`):

```python
if finding.id.startswith("vuln:") and finding.axis != AXIS_VULNERABILITY:
    raise ValueError(...)          # models.py:432-436
if finding.id.startswith("hygiene:") and finding.axis != AXIS_HYGIENE:
    raise ValueError(...)          # models.py:437-441
```

extends with two new parallel clauses (new `AXIS_LICENSE = "license"` /
`AXIS_CURRENCY = "currency"` constants mirroring `AXIS_HYGIENE`/
`AXIS_VULNERABILITY` at `models.py:35–37`):

```python
if finding.id.startswith("license:") and finding.axis != AXIS_LICENSE:
    raise ValueError(...)
if finding.id.startswith("currency:") and finding.axis != AXIS_CURRENCY:
    raise ValueError(...)
```

Additionally add the schema-level mirror: two new `allOf`/`if`/`then`
clauses in `report-schema.json`'s `$defs.finding.allOf`
(`report-schema.json:320–339`, re-verified this session as the current
span holding the `vuln:`/`hygiene:` pair), enforcing the same id-prefix ↔
axis coherence at the JSON-Schema level, mirroring the existing pair's
exact style:

```json
{
  "if": { "required": ["id"], "properties": { "id": { "pattern": "^license:" } } },
  "then": { "properties": { "axis": { "const": "license" } } }
},
{
  "if": { "required": ["id"], "properties": { "id": { "pattern": "^currency:" } } },
  "then": { "properties": { "axis": { "const": "currency" } } }
}
```

Without both the Python and schema mirrors, a mis-axed `license:`/
`currency:` finding would construct and validate silently, unlike every
other family.

**(b) id-reason/verdict coherence (new, derivable from §§ 1/2's precedence
rule).** § 1 pins that a `license:` finding is only ever emitted for
`denied`/`unknown` verdicts — the schema should enforce it. **The `then`
branch must `require` the sub-object key itself, not just describe its
properties** — JSON Schema's `properties` keyword is a no-op on an absent
key, so a clause that only says "if present, `verdict` must be X" is
vacuously satisfied by a `license:` finding that omits the `license` key
entirely, leaving it with no verdict data at all. Both clauses below fix
this with an explicit `"required": ["license"]`/`"required": ["currency"]`
inside `then`:

```json
{
  "if": { "required": ["id"], "properties": { "id": { "pattern": "^license:" } } },
  "then": {
    "required": ["license"],
    "properties": {
      "license": {
        "type": "object",
        "properties": { "verdict": { "enum": ["denied", "unknown"] } }
      }
    }
  }
}
```

Since § 2 now pins the id-reason precedence as an explicit 3-way total
order (`eol` > `over-lag` > `unknown`), the mapping to `CurrencyVerdict` is
fully determined — drafted as JSON below, not left as prose (an earlier
draft left this as prose only, unlike every other coherence clause in this
section, which is fully drafted):

```json
{
  "if": { "required": ["id"], "properties": { "id": { "pattern": "^currency:eol:" } } },
  "then": {
    "required": ["currency"],
    "properties": { "currency": { "type": "object", "properties": { "verdict": { "const": "eol" } } } }
  }
},
{
  "if": { "required": ["id"], "properties": { "id": { "pattern": "^currency:over-lag:" } } },
  "then": {
    "required": ["currency"],
    "properties": { "currency": { "type": "object", "properties": { "verdict": { "const": "supported" } } } }
  }
},
{
  "if": { "required": ["id"], "properties": { "id": { "pattern": "^currency:unknown:" } } },
  "then": {
    "required": ["currency"],
    "properties": { "currency": { "type": "object", "properties": { "verdict": { "const": "unknown" } } } }
  }
}
```

**(c) currency-provenance completeness (pairs with (b)).** Require
`latest`/`lag`/`eol_date` be **non-null** — not merely present — when
`currency.verdict` is `"eol"` or when the id's reason segment is
`over-lag` (i.e. whenever there is a "problem" to explain) — `null` stays
allowed only for `unknown` or a clean `supported`-with-no-lag state (which,
per § 2, never produces a finding at all, so this mostly matters for the
`eol`/`over-lag` cases). **`required` alone only checks key presence, not
value** — a finding that sets all three fields to explicit `null` would
still satisfy a bare `required` list. The `then` branch must additionally
**narrow the field types to exclude `null`**, mirroring the exact pattern
the schema already uses for `vuln_data.max_age_ok` (`report-schema.json:
90-98`, re-verified this session: when `max_age_ok` is a concrete boolean,
`then` narrows `source`/`snapshot_at` from `["string","null"]` down to
plain `"string"`):

```json
{
  "if": {
    "properties": { "id": { "pattern": "^currency:(eol|over-lag):" } }
  },
  "then": {
    "properties": {
      "currency": {
        "type": "object",
        "required": ["latest", "lag", "eol_date"],
        "properties": {
          "latest": { "type": "string" },
          "lag": { "type": "integer" },
          "eol_date": { "type": "string" }
        }
      }
    }
  }
}
```

### 5.5 Suppression invariants

**At most one `suppressions[]` entry per `finding_id`; waiver wins the
tie-break.** `suppressions[]` carries at most one entry per `finding_id`,
with waiver winning where both a baseline and a waiver match the same
finding, per `architecture.md:314`'s "echoed once" rule (re-verified this
session: "...the tie-break (waiver wins where both match; echoed once, via
the 6.1 rung-discriminator) is decided there"). This is a documented
MUST-hold invariant, not JSON-Schema-enforceable (Draft 2020-12 has no
native cross-array uniqueness-by-key keyword) — Story 6.1/6.8 enforce it
in code, analogous to how `ComplianceReport.__post_init__` already
enforces global `finding.id` uniqueness (`models.py:422–430`,
re-verified this session).

**Recommend a construction-time cross-check — a genuinely new check, not a
mirrored existing one.** Story 6.1 should add a `ComplianceReport.
__post_init__` check that every `suppressions[].finding_id` references an
existing `findings[].id`. **Correction from an earlier draft:** this does
NOT mirror an existing enforcement pattern — re-reading
`ComplianceReport.__post_init__` in full (`models.py:371–441`) this session
shows no runtime check cross-references `status_driver.finding_id` against
`findings[]` today. `StatusDriver`'s class docstring (`models.py:236–244`)
documents the "the id MUST equal an id present in that report's own
`findings[]`" rule as a ratified Story 1.7 contract, but it is enforced only
by convention/test coverage, never by a construction-time check in
`__post_init__` itself (confirmed: the only `finding_id`-adjacent logic
there is the narrow `EMPTY_EXTRACTION_DRIVER_ID` exact-match branch and the
separate `finding.id` global-uniqueness check, `models.py:422–430`). The
`suppressions[]` cross-check recommended here is therefore new rigor this
spike introduces, not existing rigor it extends — worth building regardless,
since a dangling suppression reference is exactly the class of silent-drift
the `finding.id` uniqueness check exists to prevent for the sibling case,
but the record should not overclaim precedent that does not exist.
Concretely: `ids = {f.id for f in self.findings}; bad = [s.finding_id for s
in self.suppressions if s.finding_id not in ids]; if bad: raise
ValueError(...)`, alongside a sibling **uniqueness** check for `suppressions[]`
itself (§ 5.5's "at most one entry per `finding_id`" invariant above is
currently only documented prose — give it the same concrete shape:
`sids = [s.finding_id for s in self.suppressions]; if len(sids) !=
len(set(sids)): raise ValueError(...)`, mirroring the existing
`finding_ids`/`set(finding_ids)` pattern at `models.py:422–430` exactly).

### 5.6 The `cli.py`/`waiver.py` wiring hand-off

The waiver-echo half of `SuppressedFinding` needs an actual owner, not a
forward reference. Recommend: **Story 6.1** (which already owns
`models.py`/`report-schema.json` in this commit) wires the waiver-echo half
— `WaiverNotice` → `SuppressedFinding{origin: "waiver"}` — inside `cli.py`'s
existing render path (today, `cli.py` threads `applied_waivers` into
`render_text` only, never into the JSON document — `cli.py:911,919–921`,
re-verified this session). **Story 6.8** wires the baseline half
(`SuppressedFinding{origin: "baseline"}`) since baseline entries don't
exist until 6.8 lands.

**This is a recommended, common-sense minor scope extension of Story 6.1's
AC, not something the AC's literal file list pre-approves.** epics.md:460's
"exactly" coordinated-update-set text names `report-schema.json` ·
`models.py` · `report.py` · the exact-N `Component` test · fixtures — it
does not name `cli.py`. Widening `waiver.py`'s local `_FINDING_ID_FAMILIES`
tuple (`waiver.py:68–76`, re-verified this session as the current span of
the comment + tuple) in the **same commit** as `models.py`'s widening is
the same category of extension: Story 6.1 already touches the sibling
tuple in `models.py`; the marginal cost of also touching `waiver.py`'s
one-line mirror and `cli.py`'s render path is near-zero next to the risk
of 6.2/6.8 shipping `license:`/`currency:` findings that are constructible
but unwaivable, or a `SuppressedFinding` type with no producer wiring it
into JSON at all. State this plainly rather than either overclaiming
pre-approval or leaving the wiring as an open question: Story 6.1's own
Dev Notes should flag this as an intentional, minor, common-sense scope
extension of the literal AC text — not something this record can silently
declare "resolved, nothing stays open," and not something left genuinely
unowned either.

**Evidence:** `waiver.py:133–141` (`WaiverNotice`), `:111–122`
(`WaiverEntry`, contrast for the required-vs-nullable comparison),
`:68–76` (the locally re-declared `_FINDING_ID_FAMILIES`), `:80–83` (the
length-symmetry comment, re-read this session to confirm what it does and
does not claim). `report-schema.json:87` (`VulnData.source`), `:263–363`
(`$defs` span), `:320–339` (the existing axis-coherence `allOf` pair).
`models.py:35–37` (`AXIS_HYGIENE`/`AXIS_VULNERABILITY`), `:371–441`
(`ComplianceReport.__post_init__`, including the `vuln:`/`hygiene:`
coherence checks at `:432–436`/`:437–441` and the finding-id uniqueness
check at `:422–430`). `architecture.md:314` ("echoed once"). `cli.py:911,
919–921` (the waiver-echo-into-text-only current state). **Owner:**
Story 6.1 (`report-schema.json`'s new `$defs.suppressedFinding` +
`license`/`currency` sub-objects + coherence clauses; `models.py`'s
`AXIS_LICENSE`/`AXIS_CURRENCY` constants + the two new
`__post_init__` clauses + the `suppressions[]`↔`findings[]` cross-check;
`waiver.py`'s tuple widening; `cli.py`'s waiver-echo-into-JSON wiring).
Story 6.8 (the baseline half of the wiring; `baseline.py`'s own validation
design, out of this spike's scope).

## 6. Worked examples (prove injectivity + grammar shape)

Every id below was checked this session with a live Python regex
`.fullmatch` against its stated family pattern and confirmed distinct from
every other row (`license:[^:\n]+:.+@.+` / `currency:(eol|over-lag|unknown):.+@.+`
— note the currency pattern's closed reason vocabulary, § 2).

| # | Finding id | Family | What it proves |
|---|---|---|---|
| 1 | `license:GPL-3.0-only:numpy@1.26.4` | license | Baseline `denied`-verdict shape: SPDX expression segment, no special characters. |
| 2 | `license:unknown:some-obscure-pkg@0.1.0` | license | The `unknown` reason token for an unresolvable license — distinct string from `unspecified` (§ 1). |
| 3 | `currency:eol:django@1.11.29` | currency | Baseline `eol`-only case (no competing `over-lag` condition). |
| 4 | `currency:eol:legacy-flask-app@0.9.0` | currency | **Fix 2's precedence rule, worked:** this component is simultaneously `eol` AND beyond `--max-lag` — the id still resolves to `currency:eol:...`, never `currency:over-lag:...`; `lag` is still populated on the `Finding` payload for transparency. |
| 5 | `currency:over-lag:requests@2.10.0` | currency | `over-lag` reason token when the component is NOT `eol` — maps to `CurrencyVerdict.SUPPORTED` (§ 5.4(b)), escalation via the numeric `lag` field only. |
| 6 | `currency:unknown:some-vendored-thing@3.0.0` | currency | No tier data available anywhere on the ladder — `unknown`, distinct from `eol`/`over-lag`. |
| 7 | `currency:eol:!python-runtime@3.8.18` | currency | The FR34 runtime-currency sentinel: `!python-runtime`, not the collidable bare literal `runtime-python` (§ 2) — structurally uncollidable with any real PyPI/conda package name. |
| 8 | `license:DocumentRef-vendor%3ALicenseRef-my-custom-1.0:acme-widget@2.0.0` | license | The SPDX `DocumentRef:LicenseRef` construct (§ 1) with its embedded colon percent-encoded (`%3A`) by `_sanitize_id_segment` before construction — the *raw*, unsanitized form (`license:DocumentRef-vendor:LicenseRef-my-custom-1.0:acme-widget@2.0.0`) was separately confirmed this session to still `.fullmatch` via backtracking, demonstrating that sanitization is applied for injectivity/stability, not because matching would otherwise fail. |

Eight rows total; this count is stated once, here, against the actual
table above (an earlier draft stated a stale row count in prose elsewhere
that didn't match its own table — this draft does not repeat that
mistake).

---

## How Story 6.1 applies this (coordinated-update-set hand-off)

Maps each pinned decision above to the exact file Story 6.1 lands it in,
per epics.md:460's coordinated-update-set text ("exactly:
`report-schema.json` · `models.py` (+ `to_json_dict` render + sort keys) ·
`report.py` runtime self-validation + `_REPORT_AXES` · the exact-13
`Component` test ... · fixtures").

1. **`models.py`** — widen `_FINDING_ID_FAMILIES` (`models.py:46–50`) with
   the two new compiled regexes (§§ 1–2); add `AXIS_LICENSE`/
   `AXIS_CURRENCY` constants (mirroring `models.py:35–37`); add the two new
   closed `StrEnum`s `LicenseVerdict`/`CurrencyVerdict` (§ 3, **not** added
   to the growable-enum list); extend `ComplianceReport.__post_init__`
   (`models.py:371–441`) with the two new id-prefix↔axis coherence clauses
   (§ 5.4(a)) and the `suppressions[]`↔`findings[]` cross-check (§ 5.5);
   extend `to_json_dict`/`_finding_dict` to render the new `license`/
   `currency`/`suppressions` shapes and extend `_finding_sort_key`
   (`models.py:520–538`) accordingly (a new field changes the total order
   over a finding — the sort key must incorporate it the same
   None-safe way every other optional field already is); a parallel
   `_suppressed_finding_sort_key`, mirroring `_coverage_sort_key`
   (`models.py:541–551`) in style, orders the new `suppressions[]` array.
2. **`report-schema.json`** — widen `$defs.finding.id.anyOf`
   (`report-schema.json:281–285`) with the two new patterns
   (`^license:[^:\n]+:[^\n]+@[^\n]+$` / `^currency:(eol|over-lag|unknown):[^\n]+@[^\n]+$`,
   the latter closed to the 3-value reason vocabulary per § 2's correction,
   mirroring the existing `vuln:` pattern's exact style otherwise); add the
   `license`/`currency` sub-object properties on `$defs.finding` (§ 5.3);
   add the four coherence `allOf` entries (§ 5.4(a)/(b)/(c)); add
   `$defs.suppressedFinding` and the top-level optional `suppressions`
   array property (§ 5.2).
3. **`report.py`** — widen `_REPORT_AXES` (`report.py:148`) to include
   `"license"`/`"currency"` — this record's earlier drafts wrongly assumed
   `_REPORT_AXES` was unchanged; epics.md:460 (re-verified this session)
   literally lists "`report.py` runtime self-validation **+
   `_REPORT_AXES`**" as in-scope. **Also build the "fails loud on a
   coverage claim for an unregistered axis" check** — re-verified this
   session by reading the whole file: no such check exists today. The
   `assessed_by_axis` dict (`report.py:232–238`) accepts a coverage claim
   for *any* axis string an `EngineResult` supplies, but the `for axis in
   _REPORT_AXES:` loop (`report.py:240`) only ever emits `AxisCoverage`
   entries for the registered axes — an unregistered axis's claim is
   **silently dropped today**, not rejected. `architecture.md:134`'s "F6"
   requirement ("a coverage claim for an unregistered axis is a hard
   error, never silently dropped") is therefore something Story 6.1 must
   **build new**, not merely verify already exists. `render_json`'s
   self-validation call is `jsonschema.Draft202012Validator
   (_packaged_schema()).validate(document)` at **`report.py:320`**
   (re-verified this session — the exact source line; an earlier draft
   cited `report.py:319`, which is `document = report.to_json_dict()`,
   the line immediately above it, not the validator call itself).
   `REPORT_SCHEMA_VERSION`/`TOOL_NAME`/`_REPORT_AXES`/`_packaged_schema()`
   (the loader, not the validator) live at `report.py:143–156`.
4. **`inventory.py`** — not literally named in epics.md:460's file list,
   but unavoidably touched: add `license_covered`/`currency_covered` to
   `Component` (`inventory.py:69–91`), their AND rules in `_merge_group`
   (`inventory.py:349–371`, via the full-constructor call — omission here
   is a loud `TypeError`) and `_fold_bare` (`inventory.py:415–478`, via
   `dataclasses.replace` — omission here is a **silent** carry-over bug,
   § 4's flip-detecting meta-test guards this). This is the same kind of
   necessary, common-sense scope extension § 5.6 already names for
   `cli.py`/`waiver.py` — the AC text's own parenthetical ("Gap-B
   merge/fold semantics defined for every new `Component` field") only
   makes sense if `inventory.py`'s merge/fold functions are actually
   edited; the file list is imprecise on this one file, not a deliberate
   exclusion.
5. **`extract/_identity.py` + `extract/pyproject.py`** — add the two new
   fields to every `Component(...)` construction site (§ 4's grep-verified
   list: 7 sites in the former, 3 in the latter).
6. **`waiver.py`** — widen the locally re-declared `_FINDING_ID_FAMILIES`
   (`waiver.py:68–76`) in the same commit (§ 5.6).
7. **`cli.py`** — wire the waiver-echo half of `SuppressedFinding`
   (§ 5.6), as a stated, intentional minor scope extension of the literal
   AC text.
8. **The exact-N `Component` test + fixtures** — widen the meta-test
   asserting `Component`'s exact field count (13 → 15) with the new
   `license_covered`/`currency_covered` fields, their `_merge_group`/
   `_fold_bare` rows, and the flip-detecting meta-test (§ 4); widen
   `tests/conftest.py`'s `make_component` (`conftest.py:33–75`) with the
   two new keyword parameters (defaulting `True`, mirroring
   `hygiene_covered`'s own default at `conftest.py:46` — **not** the
   dataclass itself, which carries no defaults; this claim is grounded in
   the fixture factory, re-verified this session, not the frozen
   dataclass); update `tests/unit/test_models.py`'s `_sample_component()`
   (`test_models.py:125–140`) and `tests/unit/test_vuln.py`'s inline
   `Component(...)` (`test_vuln.py:362–...`), the two test-local
   full-construction sites (§ 4).

## Residual Risks

- **`EffectiveConfig.license_policy`/`.currency_policy` land outside
  Story 6.1's literal coordinated-update-set** — a deliberate scope
  clarification (§ 3), not a gap: `config.py` is not in epics.md:460's
  file list, and the shipped precedent (`vuln_severity_policy` arriving in
  a later story than the schema that defines `SeverityTier`) supports
  deferring these two properties to Story 6.2/6.3.
- **`baseline.py`'s own entry-validation design** (whether `expires_at` is
  ever required for a baseline entry, how bulk acceptance is authorized)
  stays fully out of this spike's scope — Story 6.8's job (§ 5.1, § 5.6).
- **The `!python-runtime` sentinel's collision-freedom is bounded to real
  registries.** `_sanitize_id_segment` does not escape `!` either
  (re-verified this session — `!` is absent from `_LINE_BOUNDARY_ESCAPES`,
  `interfaces.py:105–116`, and from the sanitize function body,
  `interfaces.py:134–138`). The sentinel is collision-free against any
  *real* PyPI/conda registry name (which cannot legally contain `!`), but
  not against a hypothetical `RAW_MALFORMED`-mode component whose
  garbage-extracted name happens to literally contain the string
  `!python-runtime`. **Correction: this risk is NEW to this record's own
  sentinel choice, not "inherited"** — an earlier draft mislabeled it as
  inherited; `!python-runtime` did not exist before this spike, so there is
  no prior state to inherit the risk from. It remains an
  extremely-low-probability risk (garbage-extracted data, not a real
  registry entry, and RAW_MALFORMED data is already untrusted by
  definition) — not worth a redesign, but correctly attributed here as this
  record's own residual risk.
- **`--bypass` is out of `SuppressedFinding`'s scope — a distinct,
  pre-existing mechanism, not a third `origin` value — and this is a scope
  boundary, not a completeness gap in `suppressions[]`.** Re-verified this
  session: `bypass_blocking` (`waiver.py:370–388`) is explicitly documented
  as "the CLI's blanket suppression, distinct from a real waiver file's
  exact-id matching" — a transient, whole-run override mapping affected
  findings straight to the existing `Status.BYPASSED` rung (already a
  first-class lattice member), not a persistent per-finding suppression
  source. `emit_bypass_stanza` (`waiver.py:442–477`) prints a *draft*
  `.warden-waivers.yaml` stanza to stdout for a human to optionally commit
  — only once actually committed would the same finding later appear via
  `SuppressedFinding{origin: "waiver"}` in a *subsequent* run. `origin`'s
  closed 2-value set (`baseline`/`waiver`) is correct as scoped by
  epics.md's/architecture.md's literal "baseline vs waiver echo" text;
  `--bypass` is never named as a third suppression source in any FR/AC
  this spike is chartered against. **State this plainly for a JSON
  consumer:** `suppressions[]` echoes waiver-file/baseline-file-driven
  suppressions specifically; a `--bypass`-driven `Status.BYPASSED` finding
  is visible via its own `StatusDriver` (axis + finding id) and the
  report's overall `status`, but will NOT have a matching `suppressions[]`
  entry — a consumer reading only `suppressions[]` to explain every
  non-clean finding would miss bypass-driven ones, by design, since
  `--bypass` is not a committed, auditable suppression source the way a
  waiver/baseline file is.
- **Two pre-existing gaps, inherited unchanged, not introduced by this
  story** (both already filed to `deferred-work.md` per the spec's own
  Review Triage Log, not re-litigated here): `_sanitize_id_segment` never
  escapes `@`, so a `RAW_MALFORMED` component name containing a literal
  `@` could in principle break `<pkg>@<ver>` tail injectivity — this is
  pre-existing across the shipped `vuln:` family too. The family regexes'
  `[^:\n]+` middle segment only excludes literal `\n`, not the full
  line-boundary character set `_sanitize_id_segment` actually escapes
  (CR/VT/FF/NEL/LS/PS) — also inherited unchanged from the three shipped
  families.
- **Cross-story sequencing risk.** This record pins shapes for Story 6.1
  to implement mechanically; if 6.2/6.3's actual producer code discovers a
  shape here doesn't fit cleanly (e.g. a real-world SPDX expression this
  record didn't anticipate), the fix is a `bmad-correct-course` against
  this record and/or the schema — not silent producer-side improvisation,
  per this spike's own "no convention invented when a directly analogous
  shipped pattern exists" boundary.

## Gating

This record **gates Story 6.1 only** (the license/currency finding-ID
grammars, the typed verdict encoding, the suppression rung-discriminator
shape + schema placement, and the Gap-B merge/fold table for the two new
`Component` fields — all four of Story 6.10's AC-mandated deliverables).
It explicitly **does NOT gate** Stories 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8,
or 6.9 directly — each of those is gated *transitively*, through 6.1's own
HARD dependency on this record being DONE before 6.1 itself may start
(epics.md's Story 6.1 AC: "6.1 itself is HARD-gated on story 6.10's
decision record being DONE"), and then through 6.1's own status as "no
other 6.x producer story may start before 6.1 is DONE." This mirrors the
Story 1.4 precedent's explicit "gates 1.5+2.4, not 1.3" disposition line —
naming what is *not* directly gated is as load-bearing as naming what is.
