# Adversarial Reviewer-Gate Review — architecture.md (pyforge-warden)

- **Artifact:** `_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md` (status: complete, re-affirmed 2026-07-16 post-D12)
- **Method:** construct pairs of one-level-down units (stories / modules built by different agents) that each obey every stated rule to the letter yet build incompatibly. Focus: the 2026-07-15/16 D12 surfaces (multi-axis reconciliation, feeds.py, baseline vs waiver, actuator, the 6.1 amendment, two-mode policy) — cross-checked against the **shipped** code in `src/shared/packages/pyforge-warden/src/pyforge/warden/` (`interfaces.py` DefaultPolicy, `verdict.py`, `report.py:_REPORT_AXES`, `models.py` finding-id families).
- **Date:** 2026-07-16
- **Verdict: REVISE BEFORE EPIC-6 DEV.** The pre-D12 spine (inventory / lattice / triad / E1) survives attack — every pair I constructed against it is closed by an existing rule (single-model, sole-exit-owner, tighten-only, content-not-returncode). The D12 additions do not: I found **3 Critical, 4 High, 3 Medium** incompatible pairs, all on Epic-6 surfaces the shipped 1.1–1.4 contract does not yet police.

---

## CRITICAL

### F1 — License/currency verdicts have no legal representation in the frozen finding model; 6.2's producer and 6.5's policy table will key on different invented encodings

**The two units.** Agent A builds **Story 6.2** (`license.py` producer). Agent B builds **Story 6.5** (two-mode policy tables in `config.py`/policy layer).

**How both comply.**
- The shipped `models.py` admits exactly three finding-id families: `vuln:<advisory>:<pkg>@<ver>` | `hygiene:<DEP>:<subject>` | `indeterminate:<reason>:<pkg>` (`Finding.__post_init__`, `_FINDING_ID_FAMILIES`). `Finding` carries `id, axis, message, subject, severity(CVSS-shaped), kev, epss` — **no license/currency verdict slot** (`allowed|denied|unknown`, `eol|n-1|supported`). Story 6.1's coordinated set (schema gating bool, `license`/`currency` sections, `kev_date`, `epss`) adds **none of these**, and 6.1 forbids any other story widening the schema.
- Agent A must emit `denied`/`unknown` as findings. The only legal family is `indeterminate:<reason>:<pkg>` (reason is "free text, so no enum grows" — interfaces.py docstring). A obeys every rule and encodes the verdict in the reason token, e.g. `indeterminate:license-denied:openssl`.
- Agent B must implement "denied → `policy-violation`, unknown → `indeterminate` … **a policy-table flip, never a producer change**" (arch § Multi-axis reconciliation; 6.5 AC2: "no producer changes … proven by diffing only the rungs/exit"). B's table must therefore key on *something in the finding*. The axis string alone cannot distinguish `denied` from `unknown` from `allowed-but-stale`. B obeys every rule and keys on its own token guess, e.g. `indeterminate:denied:<pkg>`.

**How they diverge.** A emits `license-denied`; B matches `denied`. Both fixture suites pass locally (A's asserts findings surface; B's asserts the table escalates *its* fixture tokens). Integrated: a **configured** `--deny-licenses` run leaves a denied license at the backstop `indeterminate` — or worse, once F4's warn-mapping lands, at `warn`/exit 0. That is a **false-green under an explicitly configured gate** — the exact C0 breach the architecture exists to prevent, produced by two letter-compliant agents.

**Closing rule.** Amend § Multi-axis reconciliation + Story 6.1: *the axis-verdict encoding is part of the 6.1 amendment, not producer discretion.* Either (a) 6.1 grows the family grammar additively (`license:<verdict>:<pkg>`, `currency:<tier>:<pkg>` — with the same axis-family cross-check `ComplianceReport.__post_init__` already enforces for `vuln:`/`hygiene:`), or (b) 6.1 adds a typed `verdict` field to `Finding`. Whichever is chosen, the policy table's key MUST be the schema-validated field/family — never a free-text reason token — and a conformance test must run one shared fixture through producer→policy end-to-end (denied license + configured flag ⇒ exit 1).

### F2 — The gate-escalation path has two owners: 6.2/6.3 must ship their gates before 6.5 exists, then 6.5 demands the same behavior arrive "with no producer changes"

**The two units.** Agent A builds **Story 6.2 AC3 / 6.3 AC3** ("When either flag is set, Then the axis's `gating` flips true for the run: denied → `policy-violation` … the flags parse into the FR30 ConfigLoader tables"). Agent B builds **Story 6.5** ("the escalation is a policy-table change only … with **no producer changes**").

**How both comply.**
- The wedge build order is `6.1 → 6.2/6.3/6.4 (parallel) → 6.5 (policy integration)`. Agent A's story is DONE only when its gate AC passes — but at 6.2-time the two-mode policy layer (6.5) *does not exist*. A therefore implements the escalation in the only place available: inside/alongside the producer (its `EngineResult` rungs, or a producer-local table). Nothing forbids this — the sole-ownership rule only reserves the *lattice→exit projection* to `verdict.py`; policies "feed, never project" and any module may feed rungs.
- Agent B's AC is explicitly "no producer changes"; B builds the escalation in the ConfigLoader-driven policy table and proves it by fixture-diffing modes.

**How they diverge.** After 6.2 and 6.5 both land, the escalation exists **twice** — one flag flip drives two mutation paths into the rung stream. Best case: duplicate rungs (harmless-looking until `--warn-as-error` and driver tie-breaks disagree). Worst case: 6.5's table and 6.2's producer-local logic drift (one updated by a later story, the other not), and the mode-diff test still passes because it only diffs rungs/exit — it cannot see there are two sources. Alternatively B "fixes" it by deleting A's producer logic — which is a producer change, violating B's own AC, and un-verifying A's DONE story.

**Closing rule.** Re-sequence and re-scope: **6.2/6.3 deliver producers + flag *parsing* only (gating semantics deferred, axis verdicts land as unconfigured-mode findings); 6.5 is the sole owner of verdict-escalation for axes 3/4** — mirror the existing "verdict lattice lives only in verdict.py" rule with a new single-source rule: *"the axis policy tables (hygiene→status, CVSS thresholds, license/currency escalation, KEV/EPSS gates) live only in `config.py`'s FR30 tables; no producer maps its own verdict to a Status."* Add a meta-test (grep/AST, like the sole-ownership guard) that `license.py`/`currency.py`/`feeds.py` never construct a `Status` above `warn`.

### F3 — `actuator.py`'s report section is architecturally unconstructible: it needs a schema slot 6.1 forbids, a producer that runs after the report is already emitted, and an invoker the data flow never names

**The two units.** Agent A builds **Story 6.9** (`actuator.py`: "a failed PR-open is recorded in the post-verdict `actuation` report section"). Agent B owns the **report/verdict contract** (1.7/1.8 + 6.1: report assembled once, jsonschema-self-validated, emitted to stdout; "no other story widens the schema — the producer re-closes behind this amendment, asserted by the conformance suite"; § Data flow: `… verdict → cli emits report (stdout) + exit code` — **neither `baseline.py` nor `actuator.py` appears in the data flow at all**).

**How both comply.**
- A follows 6.9 to the letter: post-verdict, opens PRs, records failures in the report's `actuation` section. To do that A must (i) add an `actuation` section to `report-schema.json` — but 6.1 says only 6.1 amends the schema, and 6.1's coordinated set does not include `actuation`; and (ii) assemble/emit the report *after* actuation — but the verdict reads report **content** (C0), and actuation is post-verdict, so the pipeline becomes report → verdict → actuate → **re-open the report** → emit. A can comply by mutating-then-revalidating; nothing says the report is emit-once.
- B follows the frozen contract to the letter: report assembled in `report.py`, validated, emitted by `cli.py` immediately after verdict; conformance asserts no story other than 6.1 widened the schema; NFR-R3b twice-run byte-identical in `--deterministic` — which PR URLs / forge-error strings in the report **break by construction**.

**How they diverge.** Three mutually exclusive resolutions, each letter-compliant: actuation inside the report (violates 6.1's exactly-one-amendment + determinism), actuation as a second stdout document (violates the pure-JSON "one valid document or empty" stream invariant), actuation stderr-only (violates 6.9's "recorded in the … report section"). And *who invokes* the actuator is undecided: `verdict.py` may not (it is pure lattice math with a sole-ownership guard), `cli.py` is never told to — so agent A wiring it into `verdict.py` and agent B's purity guard collide outright.

**Closing rule.** Decide all three in the architecture, now: (1) fold the `actuation` section into **Story 6.1's** coordinated set (it is schema, so it belongs to the one amendment) with every field either deterministic or on the pinned volatile-field list; (2) extend § Data flow: `… verdict → baseline/waiver echo → cli emits report → [--open-fix-prs] cli → actuator (reads the emitted report, appends nothing)` — i.e., **`cli.py` is the sole invoker; the actuator consumes the final report and reports its outcome on stderr + a machine-readable `--actuation-output <file>`, never mutating the already-emitted stdout document**; (3) state explicitly that actuation is outside NFR-R3b's determinism scope because it is outside the report.

---

## HIGH

### F4 — Unconfigured-mode `warn` is a *loosening* under the shipped tighten-only rule: two agents legally build a blocking and a non-blocking unconfigured axis

**The two units.** Agent A implements 6.5 AC1 honoring **FR37** ("unconfigured → `warn` rung … exit 0, never an unconfigured red gate"). Agent B implements 6.5 AC1 honoring the **shipped `DefaultPolicy` contract** (`interfaces.py` docstring + 6.5's own third sentence: replacements of the backstop "may only tighten (toward `policy-violation`), **never loosen**").

**How both comply.** Today every non-hygiene engine finding feeds the `INDETERMINATE` backstop (`interfaces.py` lines 258–269). In the lattice, `indeterminate > warn`. A license producer's `unknown` finding therefore lands at `indeterminate`/exit 1 **today**. Agent A maps it down to `warn`/exit 0 per FR37 — a strict loosening of the backstop. Agent B refuses: tighten-only is a named acceptance property (6.5 AC1: "the change is tighten-only against `DefaultPolicy`"), so B leaves unconfigured `unknown` at `indeterminate` — and every unconfigured run on a bare PyPI manifest exits 1, which is precisely the "unconfigured red gate" FR37 forbids.

**How they diverge.** A and B produce opposite exit codes on the identical unconfigured fixture; each cites a binding rule the other violates. The contradiction is textual: 6.5's AC demands both `warn`-rung feeding and tighten-only in the same paragraph, and "tighten-only" as written ("never maps a finding toward `clean`") is ambiguous about `indeterminate → warn`, which moves toward clean without reaching it.

**Closing rule.** Redefine tighten-only precisely in the architecture: *"tighten-only means: never map a finding to `clean`/`not-applicable`, and never weaken an axis whose real policy mapping has already landed. Replacing the 1.2 conservative backstop with an axis's **first** real mapping may assign any non-clean rung, including `warn` — the backstop is a placeholder, not a floor."* Then re-derive 6.5's AC1 from it, and add the fixture: unconfigured license-`unknown` ⇒ status `warn`, exit 0; same fixture + `--deny-licenses` ⇒ `indeterminate`/`policy-violation`, exit 1.

### F5 — feeds.py: 6.3 runs *in parallel with* 6.4 yet needs the cache layer 6.4 builds — endoflife gets a second cache layout and max-age gets three owners

**The two units.** Agent A builds **Story 6.3** (currency axis; its AC says the endoflife.date fetch "follows the `_http.py` mirror-override pattern" and defines its own staleness knob: "configurable max-age (default 180 days)" for bundled data — it never mentions `feeds.py`). Agent B builds **Story 6.4** (`feeds.py` with "cache layout, lifecycle, and max-age policy documented", the OSV-DB record as template; 6.7 later says "one shared feeds.py layer").

**How both comply.** The build order is `6.2/6.3/6.4 (… parallel)`. Agent A cannot depend on a module a parallel story is still writing, and A's ACs are satisfiable without it — so A implements endoflife caching inside `currency.py` (own cache dir, own snapshot/provenance shape, own 180-day default). Agent B builds `feeds.py` exactly as the architecture's module comment says — "KEV + **EPSS + endoflife** cached-feed layer: cache, max-age, provenance (FR36; **6.4/6.7**)" — note the comment claims endoflife but the story attribution (6.4/6.7) doesn't include 6.3, so B ships a feeds.py endoflife slot nobody consumes, or omits it and the comment lies.

**How they diverge.** Two cache layouts and two provenance shapes for one feed; and **max-age policy now has three plausible owners** — `config.py` (FR30 owns "policy tables"), `feeds.py` (6.4: "max-age policy documented" per feed), and each axis (6.3's 180d, the OSV `--db-max-age` 7d precedent). A fleet operator setting one max-age knob changes KEV staleness but not endoflife staleness (or vice versa), and "absent/stale under an active policy → indeterminate" fires per-implementation, inconsistently — a staleness false-green on whichever path kept the laxer default.

**Closing rule.** (1) Re-sequence: `feeds.py`'s skeleton (cache layout, `FeedSnapshot{source, snapshot_at, max_age_ok}` type, max-age evaluation) is a named deliverable of **6.4, moved ahead of 6.3** (or extracted into 6.1 alongside the schema, since the provenance triple is already 6.1 schema material) — 6.3 and 6.7 are declared consumers. (2) Single-source rule: *"all remote-feed caching and staleness evaluation lives only in `feeds.py`; max-age **defaults** live in `feeds.py` per feed, max-age **overrides** live only in the FR30 ConfigLoader tables; axes receive a `FeedSnapshot` and never compute staleness."* (3) Fix the module-table attribution to `(FR34/FR36; 6.3/6.4/6.7)`.

### F6 — If 6.2 lands before 6.1, the shipped `report.py` *silently drops* the new axis's coverage claim while the gate flags still flip exit codes — and every per-story gate stays green

**The two units.** Agent A lands **Story 6.2** first (bmad-loop picked it up; nothing mechanical enforces the wedge order — epics.md's order is "recommended", and the sprint feed is regenerated YAML). Agent B has landed only the **frozen 1.x contract** (shipped `report.py`: `_REPORT_AXES = (AXIS_HYGIENE, AXIS_VULNERABILITY)`; coverage is assembled per that tuple — an `EngineResult.coverage` entry for `axis="license"` matches nothing and vanishes; the architecture itself states this: "without which a new axis's coverage claim is silently dropped").

**How both comply.** A registers behind the open `Engine` seam with `axis="license"` — the architecture says this is the sanctioned mechanism, "no new interface". A's findings pass through `DefaultPolicy` fine (findings are axis-open), so A's unit fixtures pass. A does **not** widen the schema — which is exactly what the "no other story widens the schema" conformance rule demands. B's contract tests pass untouched.

**How they diverge.** Integrated pre-6.1: license findings appear and (post-F2 fix) gate — but the license axis's `AxisCoverage` is silently discarded, `gating` has no schema slot, and the `license` section doesn't exist. The report claims full coverage over 2 axes while a third axis assessed components and influenced the exit code — a coverage lie invisible to every existing gate, in a tool whose acceptance spine is coverage honesty. Note this is not only an ordering accident: the same silent-drop fires for any future axis typo (`axis="licence"`).

**Closing rule.** Two teeth: (1) make the drop loud — a standing invariant (land it in 6.1): *"`report.assemble_report` MUST raise / feed an `error` rung when any `EngineResult` carries a finding or coverage claim whose axis ∉ `_REPORT_AXES`"* — unknown axes become fail-loud, converting the ordering hazard into an unmissable red. (2) Encode `6.1 ≺ {6.2, 6.3, 6.4, 6.7, 6.8, 6.9}` as a **hard dependency in `sprint-status.yaml`/the loop policy**, not prose ("recommended") order.

### F7 — The per-axis `gating` bool has two writers: the report field and the verdict behavior can disagree

**The two units.** Agent A builds the **report side** of `gating` (6.1 adds "a per-axis `gating` bool" to the schema; `report.py` assembles axis sections — but from what source? `EngineResult` has `findings/errors/coverage` only; `AxisCoverage` has no gating field — so A plumbs it from whatever A picks: the producer's coverage claim, a new EngineResult field, or config). Agent B builds the **behavior side** (6.2/6.5: the CLI/config flags "parse into the FR30 ConfigLoader policy tables"; the escalation "is a policy-table change only").

**How both comply.** The architecture assigns `gating` to the schema (6.1) and the flip to "a policy-table flip" (6.5) but never states the single source the report field is rendered FROM. A reading "the axis's gating flips true" (6.2 AC3 — phrased as a property *of the axis*) plumbs it via the producer; B reading "policy-table change only" puts truth in `config.py`. Both are quotes.

**How they diverge.** Producer-carried `gating` and table-carried escalation update independently: a config-file (non-CLI) policy activation flips B's table but not A's producer-carried bool → the report prints `gating: false` while the run exits 1 on that axis (or the inverse). The machine contract lies about its own gate — downstream fleet tooling (the cf_atlas consumer) keys dashboards on that field.

**Closing rule.** One sentence in § Multi-axis reconciliation: *"`gating` is computed only by the FR30 ConfigLoader (flag/config resolution) and injected into `report.py` at assembly; producers never see or emit it."* Plus a conformance fixture asserting report-`gating` ⇔ escalation behavior on the same run (config-file-activated, no CLI flag — the path most likely to desync).

---

## MEDIUM

### F8 — baseline.py and waiver.py are two implementations of one suppression mechanism, and the stated tie-break ("waiver wins, echoed once") has no owning module or pipeline position

**The two units.** Agent A builds **`waiver.py`** (FR24–26: schema-validate, "enforces expiry", feeds `bypassed`; routed via `--bypass` in the data flow). Agent B builds **`baseline.py`** (6.8: finding-ID-keyed, "expiry = waiver semantics", "echoed in the report (loud, `bypassed`-style)"; **absent from § Data flow entirely**).

**How both comply.** "Expiry = waiver semantics" is prose, not a shared function: A and B each implement `expires_at` parsing (date-only vs datetime, timezone assumption, expires-*on*-the-day inclusive or exclusive) independently — both schema-valid, both tested. The overlap winner is stated ("waiver wins where both match — one suppression, echoed once") but no module is named as the place that sees *both* sets, and no order exists in the data flow: A applies waivers where the flow says; B, unplaced, picks either side of A.

**How they diverge.** (i) On the shared entry's expiry day, one module suppresses and the other re-blocks — the same finding is simultaneously `bypassed` and gate-driving depending on which module touched it first. (ii) With baseline applied before waiver, a doubly-matched finding is echoed by both → "echoed once" fails; applied after, the waiver already consumed it and the baseline echo (which 6.8 requires) never appears. Also unstated: is a *baselined* finding's rung literally `bypassed` ("bypassed-style" hedges) — if yes, report consumers can't distinguish waived from baselined debt; if no, a new rung needs 6.1 schema work nobody scoped.

**Closing rule.** (1) Extract one shared suppression primitive: *"finding-ID matching + expiry evaluation live in one function (suggest `waiver.py:suppression_match(entry, finding, now) -> Live|Expired`), imported by both; expiry is exclusive-UTC-midnight (pick one, write it down)."* (2) Name the sequencing owner in § Data flow: `policy rungs → baseline.apply → waiver.apply (waiver consumes first on overlap) → verdict` — waiver-wins becomes an ordering fact, not a hope. (3) Decide the baselined rung: reuse `bypassed` with a `suppressed_by: baseline|waiver` driver discriminator (a 6.1 field, so scope it there).

### F9 — Dry-run and real-run cannot share the actuator code path under the flag-scoped socket carve-out as written — and dry-run's stdout collides with the pure-JSON invariant

**The two units.** Agent A implements 6.9's **duplicate protection** ("an existing open PR for the same finding ID is detected and skipped") as part of the shared plan-then-execute path, so `--fix-prs-dry-run` also reports "would skip: PR #N exists" — the only way dry-run output faithfully predicts the real run. Agent B implements the **C0c carve-out** exactly as the binding rule states: "scoped to `actuator.py` **under the flag**" — and the only flag the carve-out text names is `--open-fix-prs`.

**How both comply.** A: nothing says duplicate detection is real-run-only, and a dry-run that can't see existing PRs prints intents the real run would refuse — arguably a dishonest dry-run. B: the harness allows sockets only for `actuator.py` under `--open-fix-prs`; deny-by-default everywhere else, asserted globally.

**How they diverge.** A's dry-run performs forge **reads** (duplicate check) under `--fix-prs-dry-run` — B's harness kills it. Either the dry-run crashes (A's story red against B's gate), or someone widens the carve-out to the dry-run flag — silently growing the egress surface the rule was written to pin. Separately: 6.9 says dry-run "prints the would-be PRs (machine-readable to stdout under NFR-I3 purity rules)" while the report *also* goes to stdout and the invariant is "stdout is **one** valid document or empty" — two agents resolve that as two-documents vs embed-in-report vs separate file, incompatibly.

**Closing rule.** Decide both: *"dry-run is offline by definition — it performs zero egress; duplicate detection is real-run-only, and dry-run output carries `duplicate_check: not-performed` per intent (honest, not predictive). The carve-out flag is exactly `--open-fix-prs`."* And: dry-run intents go to `--actuation-output <file>` (or stderr), never stdout — stdout stays the report's alone (aligns with F3's closing rule).

### F10 — KEV/EPSS enrichment has no defined mutation point on frozen findings: 6.4 and 6.7 can enrich at different pipeline positions and dedup makes the difference observable

**The two units.** Agent A builds **6.4** (KEV): `Finding` is a frozen dataclass, so `kev: true` must be set at construction — A has `vuln.py` consult `feeds.py` while producing findings. Agent B builds **6.7** (EPSS) from "6.4's work is the direct template" but reads the layering differently: B adds a post-policy enrichment pass that rebuilds findings with `epss` before report assembly (also legal — nothing places enrichment).

**How both comply.** No rule locates enrichment. A's placement is upstream of `DefaultPolicy`'s first-wins dedup; B's is downstream of it. Both pass their own ACs ("the finding carries `kev: true`" / "carries `epss {score, percentile}`").

**How they diverge.** When the same finding id arrives from two engine results (the dedup path `interfaces.py` explicitly supports), A's upstream enrichment survives dedup only if the *first-registered* occurrence was enriched; B's downstream pass enriches whatever survived. Result: findings with KEV but no EPSS (or the reverse) on the same advisory, and — once `--fail-on-kev`/`--min-epss` gate — the **gate outcome depends on engine-registration order**, violating determinism in spirit while every stated rule holds. Rebuild-a-frozen-dataclass downstream also risks desync with the rung drivers already minted against the pre-enrichment object.

**Closing rule.** Place it: *"feed enrichment (KEV, EPSS) happens exactly once, in `vuln.py` at finding construction, via `feeds.py` lookups; post-policy code never rebuilds a `Finding`."* Add a fixture: duplicate advisory across two engine results ⇒ the surviving finding carries both `kev` and `epss`, independent of registration order.

---

## Counts

| Severity | Count | Findings |
|---|---|---|
| Critical | 3 | F1, F2, F3 |
| High | 4 | F4, F5, F6, F7 |
| Medium | 3 | F8, F9, F10 |
| **Total** | **10** | |

## Disposition

Every finding closes with a rule small enough to land as: (a) edits to § Multi-axis reconciliation + § Data flow + the single-source-of-truth rules in architecture.md, (b) scope moves into Story 6.1 (F1 encoding, F3 actuation section, F8 rung discriminator, part of F5), and (c) two mechanical teeth (F6's unknown-axis fail-loud + hard sprint dependency; F2's no-Status-above-warn producer meta-test). None invalidates the spine; all ten are cheap now and expensive after 6.2/6.3/6.4 run in parallel.
