---
doc_type: deferred-work-ledger
project: pyforge-warden
date: 2026-07-29
status: promoted-verbatim
---

# pyforge-warden — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-29 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown, and this repo has already lost data that way
(pyforge-atlas's live ledger is still truncated to 11 of 64 entries, collateral of the
2026-07-19 copy failure). Until today this project had **no tracked ledger at all**, so
its entire deferred-work record — 62 KB — existed only in
scratch space. Found by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current. The one intentional edit is
id renaming, below.

Durability first; curation is owned follow-up work.

## Ids renamed on promotion

- `DW-1` → **`DW-FU-6-3`** (story `6-3-currency-axis-producer-gate-flags`) — bmad-loop emits a bare
  `DW-<n>` per run, which collides with the next damped story; renamed on promotion.
- `DW-2` → **`DW-FU-5-1`** (story `5-1-actionable-diagnostics-safe-by-default-posture`) — bmad-loop emits a bare
  `DW-<n>` per run, which collides with the next damped story; renamed on promotion.

---

# Deferred Work

## DW-1-1-1 — The loop's exact `[verify]` command (`pixi run -e python-deptry-osv-scanner python-deptry-osv-sc…

- source_spec: `_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/spec-1-1-frozen-contract-verdict-lattice-projection-safety.md`
  summary: The loop's exact `[verify]` command (`pixi run -e python-deptry-osv-scanner python-deptry-osv-scanner-test`, unfrozen) fails environmentally in every bmad-loop worktree — pixi-build-python 0.8.3 panics (`tools.rs:461` byte-index underflow) when the build `workDirectory` exceeds ~250 chars (run-worktree roots are ~162 chars), and behind it any successful unfrozen re-solve in a worktree rewrites `pixi.lock` with worktree-absolute paths for the gitignored `file://…/build_artifacts` channel (toxic to commit via the loop's `git add -A` squash-merge); switch `.bmad-loop/policy.toml` `[verify]` to `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` (or export `PIXI_FROZEN=true` in the engine env / shorten the runs-dir path / pin pixi-build-python past the underflow), and note the related risk that a stale pixi build cache can resolve the package to non-worktree sources, so the verify gate should always run `--frozen` from the worktree root.
  evidence: Reproduced at baseline (before this story's changes) and re-confirmed after — the unfrozen solve dies with "the build backend (pixi-build-python) exited prematurely" during the `python-deptry-osv-scanner` env solve, while `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` passes the identical suite (111 passed at implementation, all green at review patch close); a controlled experiment showed the same package solves at a 149-char root and panics at 162 (path-length-driven), and the `detached-environments = true` + `build_artifacts` symlink workaround made the exact unfrozen command pass 111/111 before both tracked files were reverted to keep the story diff clean.

  status: open

## DW-BMAD-LOOP-1 — `scm.isolation = \"worktree\"` + `cleanup.trim_artifacts = true` silently lose any dev/review-se…

- source_spec: `docs/specs/bmad-loop-adoption.md`
  summary: "`scm.isolation = \"worktree\"` + `cleanup.trim_artifacts = true` silently lose any dev/review-session update to a gitignored `implementation-artifacts/` file (`sprint-status.yaml`, `deferred-work.md`, a newly-authored `spec-{story-key}.md`) once the run's worktree is torn down after a successful merge. `scm.worktree_seed` copies these files INTO a fresh worktree at start, but nothing copies the worktree's updated copies back OUT before cleanup deletes it — only git-tracked source changes survive the squash-merge, because `implementation-artifacts/` is gitignored by design (CLAUDE.md Tier 3). Net effect: the code ships correctly, but the BMAD paper trail (the sprint-status flip to `done`, the story's own `spec-*.md`, any `deferred-work.md` append the session made) silently vanishes unless a human happens to have a copy in hand and manually reconstructs it. Not story-scoped — will recur for every future bmad-loop-driven story until fixed at the orchestrator level. Fix candidates: (a) sync the worktree's `implementation-artifacts/` back to the main checkout before merge/cleanup (the `worktree_seed` copy, in reverse); (b) don't trim/delete a run's worktree until its gitignored-artifact delta is reconciled; (c) have the merge step in `bmad-loop resume` explicitly copy `implementation-artifacts/` back regardless of git-tracked status."
  evidence: Run `20260716-043830-a9bb` (story `1-5-osv-scanner-as-the-second-engine`, 2026-07-16) — after `bmad-loop resume` completed the merge (`ce2ed97bc4`) and the worktree was torn down, the main checkout's `sprint-status.yaml` still read `1-5-osv-scanner-as-the-second-engine: backlog`, and the worktree's updated `deferred-work.md` (8682 bytes, one new section appended by the review session) plus the newly-authored `spec-1-5-osv-scanner-as-the-second-engine.md` (25308 bytes) were both gone — `.bmad-loop/archive/` had no copy for this run, and `trim_artifacts=true` had already removed `worktrees/`. All three were manually reconstructed from conversation context (the spec had been read in full during the pre-merge spec-approval review) rather than recovered from disk.

  status: open
## Deferred from: code review of spec-1-1-frozen-contract-verdict-lattice-projection-safety (2026-07-13)

- `status_driver.finding_id` has no referential integrity against `findings[]` (models.py:281) — a `policy-violation` report whose driver names a finding absent from `findings[]` validates at both the model and schema layers; blanket enforcement is not safely expressible in 1.1 because the error-driver grammar is owned by Story 1.7 and waiver-suppression semantics by Epic 3. Revisit when 1.7 lands the error-driver grammar.
- PEP-440-equal version spellings (`2.31` vs `2.31.0`) split component identity, double-count inventory, and fork finding IDs across runs whose extractor source flips (inventory.py:94) — `packaging` is already a declared dep that could canonicalize, but changing frozen identity semantics needs spec grounding; owned by the extractor/producer stories (1.3+/2.x).

## Deferred from: code review of spec-1-2-interfaces-null-engine-regression-harness-socket-deny (2026-07-13, Opus cycle 3)

- Poetry/PDM `pyproject.toml` whose dependencies live outside `[project].dependencies` (`[tool.poetry.dependencies]`, `[tool.pdm]`, optional-dependencies, dependency-groups) currently scans as `not-applicable`/exit-0 — a residual false-green for exit-code-only CI consumers (the only signal is a stderr line an exit-code check never sees). The single-manifest `[project].dependencies`-only extractor is by-design for 1.2; **section-aware discovery + the D2 fail-closed split is owned by Story 1.9.** When 1.9 lands, a dependency-bearing Poetry manifest must resolve to `indeterminate`/exit-1 (or a parsed inventory), never `not-applicable`. A CHARACTERIZATION test (`test_poetry_only_deps_scan_as_not_applicable_KNOWN_GAP` in tests/unit/test_discovery_extract_cli.py) pins the current behavior so 1.9 must consciously flip it. (Also raised — and already recorded — in the dev-session review's defer; re-confirmed by the Opus cycle-3 Blind Hunter.)

## Deferred from: code review of spec-1-3-deptry-as-the-first-engine (2026-07-14, independent Opus cycle)

- **RESOLVED (was deferred from 1.2):** Poetry/PDM deps outside `[project].dependencies` no longer scan as a not-applicable false-green — deptry reads `[tool.poetry.dependencies]` natively (FR9), so 1.3's deptry engine surfaces them as DEP002 (`warn`). The 1.2 characterization test `test_poetry_only_deps_scan_as_not_applicable_KNOWN_GAP` was rewritten to `test_poetry_only_deps_are_covered_by_deptry_natively`.
- Unrecognized deptry record *shape* (not an unknown DEP code — a record whose structure we don't model) escalates the WHOLE scan to `error`/exit-2, while an unknown DEP *code* gracefully degrades to `indeterminate`. A future deptry minor that adds/renames a per-record field would flip every scan to a fleet-wide false-error. Bounded today by the deptry conda version pin (0.25.1) + the schema tests, so deferred as a forward-compat hardening: when deptry is bumped, consider degrading an unrecognized record shape to `indeterminate` (fail-closed-soft) rather than `error` (fail-closed-hard), matching the unknown-code path. (Opus review, medium; not reachable with the pinned deptry.)
- `DeptryEngine` sets `deps_assessed == inventory.count` on any successful parse, regardless of whether deptry actually analyzed any source; a project deptry can't resolve (non-standard layout, or `[tool.deptry] extend_exclude` covering the only importing file) → deptry emits `[]` → report reads `clean`/fully-covered/exit-0. Same class as 1.2's no-scan gap; **owned by Story 1.7's no-scan guard** (already listed in the 1.3 spec residual risks). A future coverage-floor gate (Story 3.1/FR19) must not pass on zero real analysis.

## Deferred from: code review of spec-1-4-osv-db-offline-provisioning-spike (2026-07-14, Blind Hunter + Edge Case Hunter, Opus)

## DW-1-4-1 — The 1.4 fixture proves offline OSV matching only for the literal pin `pdos-vuln-fixture==1.0.0`;…

- source_spec: `_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/spec-1-4-osv-db-offline-provisioning-spike.md`
  summary: The 1.4 fixture proves offline OSV matching only for the literal pin `pdos-vuln-fixture==1.0.0`; PEP-503 name-normalization (e.g. `pdos_vuln_fixture` / `PDOS.Vuln.Fixture`) and PEP-440 version-equivalence (`1.0` vs `1.0.0`) matching against the offline DB are unexercised — Story 1.5's osv-input synthesis + Story 2.1's conda↔pypi identity map must ensure a differently-spelled-but-equivalent package still matches, or a real CVE could be silently missed.
  evidence: osv-scanner matches by normalized package name + version; the spike deliberately used a synthetic exact-name/exact-version fixture for hermeticity, so the normalization paths never ran. Raised by the Edge Case Hunter (EC11) and reflected in the decision record's Residual risks § (version-exact matching only).
- **RESOLVED (Story 5.2, 2026-07-24):** The 1.4 proof test establishes offline behavior by passing `--offline` and pointing at the fixture DB, but does NOT observe the osv-scanner subprocess's network (the in-process socket-deny harness cannot patch a child process) — a future osv that egressed under `--offline` (telemetry, transitive resolution) would pass silently; NFR-S2's central "never fetch silently" claim was trusted, not measured, for the subprocess.
  evidence: `conftest.py`'s socket-deny harness is in-process only (its own docstring notes engine subprocesses are outside it); nothing asserted zero connections occurred. Closed via the lighter "egress counter" alternative this item itself named: `tests/conformance/test_corpus_egress_counter.py` wraps the WHOLE `warden scan` process tree (CLI + every forked engine subprocess) in `strace -f -e trace=network` over the full 5.2 corpus, asserting 0 `connect`/`sendto` syscalls (Linux-only, skip-if-`strace`-unavailable — never a hard requirement elsewhere); live-verified green. Originally: source_spec `_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/spec-1-4-osv-db-offline-provisioning-spike.md`, raised by the Blind Hunter (finding 7).

  status: done (resolution recorded inline, date unknown)
## Deferred from: code review of spec-1-5-osv-scanner-as-the-second-engine (2026-07-16, review pass)

- `DefaultPolicy.evaluate` (interfaces.py, untouched by the 1.5 diff) unconditionally stamps every engine `ErrorRecord`'s rung driver with `axis=AXIS_VULNERABILITY` regardless of source engine/error kind — pre-existing since 1.2/1.3 (already true for `DeptryEngine`'s own hygiene-axis errors), already explicitly tracked in `interfaces.py`'s own docstring as owned by Story 1.7's error-grammar work; `OsvEngine`'s new errors merely ride the same known, pre-existing path. Owned by Story 1.7.

## Deferred from: code review of spec-1-6-severity-gate-verdict-composition-end-to-end (2026-07-16, review pass)

- `hygiene.py`'s `DEFAULT_HYGIENE_POLICY` golden-equality unit test lacks the structural "never maps to `clean`" guard that 1.6's review just added for `DEFAULT_VULN_SEVERITY_POLICY` (`test_default_vuln_severity_policy_never_maps_to_clean`, `test_vuln.py`) — pre-existing since 1.3, out of 1.6's scope (`hygiene.py`/`test_hygiene.py` untouched by design). Add the equivalent `Status.CLEAN not in DEFAULT_HYGIENE_POLICY.values()` assertion to `test_hygiene.py` when that module is next touched.
- `DEFAULT_HYGIENE_POLICY` (hygiene.py) and `DEFAULT_VULN_SEVERITY_POLICY` (vuln.py) are both unprotected mutable module-level dicts — nothing stops an in-process mutation (accidental or malicious) from altering the effective policy for the remainder of the run. Same latent, low-risk pattern in both tables; no exploit path identified (both are hardcoded, non-overridable-by-config in v1). Consider a `MappingProxyType` wrap or a frozen-dict guard when Story 3.1's `ConfigLoader` next touches this seam.

## Deferred from: code review of spec-6-3-currency-axis-producer-gate-flags (2026-07-23, review pass)

## DW-6-3-1 — The report schema has no `runtime_python` field on `ComplianceReport`/the currency section — epi…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-3-currency-axis-producer-gate-flags.md`
  summary: The report schema has no `runtime_python` field on `ComplianceReport`/the currency section — epics.md's Story 6.3 AC text ("`runtime_python` currency is a first-class field") and the 6.10 decision record (§ 2, which names `runtime_python` as the report-section field distinct from the `!python-runtime` finding-id sentinel) both assume such a field exists, but Story 6.1's actual coordinated schema-update set never included it and `models.py` confirms it was never added. 6.3 cannot add it now (no story after 6.1 may widen the frozen schema) — it represents the Python runtime's currency exclusively via its own `currency:<reason>:!python-runtime@<ver>` `Finding`, which is the only constraint-compliant resolution. Worth a small follow-up: either a documented correction to epics.md/the decision record acknowledging the finding-only representation, or a deliberate future schema amendment if a dedicated report-level field is later judged worth the cost.
  evidence: `grep -rn "runtime_python" src/pyforge/warden/*.py report-schema.json` returns nothing outside `currency.py`'s own docstring; `CurrencyInfo` (models.py) carries only `verdict/latest/lag/eol_date/tier`, no report-section-level runtime slot exists on `ComplianceReport` beyond the singular `currency_data: FeedProvenance | None`. Raised independently by the Blind Hunter review pass; the root cause predates this story (Story 6.1's execution never implemented what the decision record assumed), so it is not this story's defect to fix.

  status: open

  verified: 2026-07-30 — `runtime_python` appears 0 times in both `data/report-schema.json` and `models.py` — the field was never added.

## DW-6-3-2 — `scripts/refresh_endoflife_feed.py` fetches one HTTP request per registry product slug with no r…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-3-currency-axis-producer-gate-flags.md`
  summary: `scripts/refresh_endoflife_feed.py` fetches one HTTP request per registry product slug with no rate limiting, backoff, or retry — as the bundled `lts-registry.yaml` grows, this is an unaddressed throttling footgun against the real endoflife.date API, and any single transient failure (including a 429) aborts the entire refresh with no partial-progress recovery.
  evidence: Raised by the Blind Hunter review pass; confirmed by reading `scripts/refresh_endoflife_feed.py`'s per-product fetch loop, which has no `time.sleep`/backoff/retry logic between requests. Out of this story's scope (a real design decision — retry policy, backoff curve, partial-write semantics — not a trivial patch); the script is human-run, low-frequency, and off the `scan` runtime path, so this is a hardening item for whenever the registry's product count grows enough to matter.

  status: open

## DW-6-3-3 — `_resolve_from_lines`/`_resolve_from_cycles` (currency.py) compute `lag` by counting entries rel…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-3-currency-axis-producer-gate-flags.md`
  summary: `_resolve_from_lines`/`_resolve_from_cycles` (currency.py) compute `lag` by counting entries released strictly after the matched one (`>`, not `>=`) — two lines/cycles sharing an identical `released`/`releaseDate` value mutually exclude each other from the count, which can report `lag=0` for a component tied with a same-day alternate release rather than genuinely latest.
  evidence: Raised by the Blind Hunter review pass; confirmed by reading both resolver functions' `sum(1 for ... if released > matched_released)` comparisons. Judged a genuinely ambiguous edge case (whether same-day releases should count as "behind" each other is not obviously wrong either way) rather than a clear defect, and real-world same-day-release collisions across a product's own release history are rare — deferred rather than patched this pass.

  status: open

## DW-6-3-4 — `currency.py`'s `DEFAULT_CURRENCY_POLICY` and `config.py`'s `EffectiveConfig.currency_policy` pr…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-3-currency-axis-producer-gate-flags.md`
  summary: `currency.py`'s `DEFAULT_CURRENCY_POLICY` and `config.py`'s `EffectiveConfig.currency_policy` property hand-duplicate the same `{EOL: WARN, UNKNOWN: WARN}` mapping in two files with no import relationship — only a golden-equality unit test catches drift between them, not the type system. This continues an existing pattern from Story 6.2's `DEFAULT_LICENSE_POLICY`/`license_policy` pair, not a new problem 6.3 introduced.
  evidence: Raised by the Blind Hunter review pass; confirmed both definitions exist independently in `currency.py` and `config.py`. A real fix (deriving one from the other, or a shared module-level table both axes import) would touch the pre-existing 6.2 pattern too — a cross-cutting consolidation out of this story's scope.

  status: open

## DW-6-3-5 — The endoflife.date cache reuses `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (7 days, tuned for KEV's frequ…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-3-currency-axis-producer-gate-flags.md`
  summary: The endoflife.date cache reuses `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (7 days, tuned for KEV's frequent-refresh cadence) rather than a longer default, despite being provisioned by a manual, human-cadence script — any team that doesn't wire up a weekly `refresh_endoflife_feed.py` cron degrades every tier-2 resolution to `unknown` after one week, incongruous with the bundled LTS registry's considerably more lenient 180-day default for conceptually similar curated, infrequently-updated data.
  evidence: Raised by the Blind Hunter review pass. This story's spec explicitly required reusing `feeds.py`'s shared cache/staleness layer "verbatim" (per epics.md's 6.4 AC: "axes never compute staleness," defaults live only in `feeds.py`) — the fail-closed-to-unknown behavior is honest and NFR-37-compliant, not a bug, but the specific 7-day default may be worth reconsidering as a per-feed-type default (or a config override) in a future cross-axis staleness-defaults pass; changing it unilaterally here would mean either touching the shared KEV-serving constant or building a private override, both against this story's explicit boundaries.

  status: open

  verified: 2026-07-30 — `feeds.py:98` still defines the shared `DEFAULT_FEED_MAX_AGE_DAYS = 7`, and `vuln.py:146` imports that same constant — no endoflife-specific age exists.
## Deferred from: follow-up code review of spec-6-3-currency-axis-producer-gate-flags (2026-07-23, independent follow-up review pass)

## DW-6-3-6 — Both currency resolvers parse and DROP the `lts` boolean (registry `lts_lines` entries and endof…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-3-currency-axis-producer-gate-flags.md`
  summary: Both currency resolvers parse and DROP the `lts` boolean (registry `lts_lines` entries and endoflife.date cycles both carry it) — `_Resolution`/`CurrencyInfo` retain no LTS signal, so Story 6.5's `--require-lts` escalation ("block on non-LTS where an LTS exists") cannot be evaluated from the data this producer emits; 6.5 will need either a producer amendment threading LTS-ness through (plus a deliberate schema decision, since `CurrencyInfo` is frozen) or a re-resolution inside the verdict layer that would strain the producer/verdict ownership split.
  evidence: `currency._resolve_from_lines`/`_resolve_from_cycles` never read the `lts` key; `CurrencyInfo` (models.py) carries only verdict/latest/lag/eol_date/tier. The 6.3 spec's Never section explicitly assigns the `is_lts`-style schema question to Story 6.5 ("both are Story 6.5's sole design/ownership") — logged so 6.5 plans for the missing input rather than discovering it mid-implementation. Raised by the follow-up Blind Hunter pass.

  status: open

## DW-6-3-7 — `currency:`/`license:` finding ids (`<axis>:<reason>:<name>@<version>`) carry no ecosystem discr…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-3-currency-axis-producer-gate-flags.md`
  summary: `currency:`/`license:` finding ids (`<axis>:<reason>:<name>@<version>`) carry no ecosystem discriminator while `inventory.merge_components` deliberately keeps the same `(name, version)` DISTINCT across ecosystems — a mixed conda+pypi inventory carrying the same package name@version in both ecosystems (e.g. a pixi env and a requirements.txt both pinning requests 2.31.0) produces two components whose axis findings share ONE id, breaking id-injectivity assumptions (an id-matched waiver suppresses both at once). Pre-existing pattern from Story 6.2's license ids which 6.3 merely mirrors; the id grammar is pinned by the 6.10 decision record § 2, so any fix is a cross-axis, decision-record-level amendment, not a producer patch.
  evidence: `license.py` and `currency._currency_finding` both build `<axis>:<reason>:<name-segment>@<version-segment>` with no ecosystem segment; `merge_components` groups by `(ecosystem, name, version)` and keeps ecosystems distinct by design ("honest count inflation, stated"). Raised by the follow-up Edge Case Hunter pass.

  status: open

## DW-6-3-8 — The frozen 6.1 model invariant ("currency eol/over-lag finding requires non-null latest/lag/eol_…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-3-currency-axis-producer-gate-flags.md`
  summary: The frozen 6.1 model invariant ("currency eol/over-lag finding requires non-null latest/lag/eol_date", models.py) makes endoflife.date's documented BOOLEAN `eol` shapes partially inexpressible — `eol: true` (already-EOL, no date published) and `eol: false` on a behind match can only degrade to `currency:unknown`, understating a real EOL as unknown (still WARN in v1 so no gate change, but the verdict text is wrong for the axis whose brand is age-honesty). The expressible half (`eol: false` + fully current → supported, no finding, killing systematic `currency:unknown` noise on real provisioned snapshots) WAS patched this pass. Candidate for a deliberate future schema amendment (nullable eol_date on `currency:eol` findings, or an explicit dateless-EOL marker) — not fixable by any post-6.1 story under the no-schema-widening rule.
  evidence: Confirmed live this pass — implementing verdict=EOL/eol_date=None for `eol: true` turned the suite red at models.py:437 ("currency eol/over-lag finding requires non-null latest/lag/eol_date"); the 6.3 spec's Block-If forbids widening the frozen 6.1 schema, so `_resolve_from_cycles` now documents and degrades those shapes instead. Raised by the follow-up Edge Case Hunter pass (partially patched; remainder schema-blocked).

  status: open
## Deferred from: second follow-up code review of spec-6-3-currency-axis-producer-gate-flags (2026-07-23, bmad-dev-auto review pass)

## DW-6-3-9 — `ComplianceReport.__post_init__`'s duplicate-finding-id invariant turns ANY producer-side id col…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-3-currency-axis-producer-gate-flags.md`
  summary: `ComplianceReport.__post_init__`'s duplicate-finding-id invariant turns ANY producer-side id collision into a report-killing internal error — `assemble_report` runs OUTSIDE the engine seam, so the `ValueError` falls through to `cli.py`'s last-resort net (internal-error exit, NO report emitted, violating the "report still emitted" doctrine every engine crash honors). The currency axis's ecosystem-variant collision (the dominant trigger: it emits an `unknown` finding for every unresolved component) was deduped in-producer this pass, but the license axis retains the same latent pattern — `license.py` dispatches per-ecosystem and can mint colliding `license:unknown:<pkg>@<ver>` ids for the same name+version in conda+pypi when both resolve unresolvable — and the model-level hard-crash posture itself (vs. a typed internal-error record with the report still emitted) is a 6.1-frozen design worth a deliberate revisit alongside the already-ledgered ecosystem-discriminator grammar amendment (separate entry above — do not merge or modify it).
  evidence: Live-reproduced pre-patch this pass — a project with pyproject.toml + pixi.toml both declaring `mystery-pkg==1.0.0` (an ordinary dual-manifest shape) crashed `scan` end-to-end: `merge_components` keeps `(ecosystem, name, version)` identities distinct, currency resolution is ecosystem-agnostic, both components minted `currency:unknown:mystery-pkg@1.0.0`, and models.py's uniqueness check raised straight through to the internal-error exit with no report. Post-patch the same project emits a full report with one deduped finding (verified live). license.py:638's per-ecosystem dispatch leaves the narrower license-side collision reachable (e.g. conda recipe metadata + pypi metadata both unresolved at the same name+version). Raised by the second-pass Blind Hunter.

  status: open
### DW-FU-6-3: Follow-up review still recommended for 6-3-currency-axis-producer-gate-flags after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-6-3-currency-axis-producer-gate-flags.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 1) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260723-184834-a653; this entry preserves the lingering recommendation for a deliberate later review.
status: open

## Deferred from: code review of spec-6-5-two-mode-policy-integration (2026-07-24, Blind Hunter + Edge Case Hunter, Opus)

## DW-6-5-1 — The bundled `data/lts-registry.yaml` carries a fixed `updated:` date (currently `2026-07-06`) an…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-5-two-mode-policy-integration.md`
  summary: The bundled `data/lts-registry.yaml` carries a fixed `updated:` date (currently `2026-07-06`) and a 180-day `_REGISTRY_MAX_AGE_DAYS`, but — unlike the KEV and endoflife.date caches, which a `refresh_*_feed.py` script re-provisions — it is a packaged resource with NO runtime refresh path. Story 6.5 makes this consequential: once currency gating (`--max-lag`/`--require-lts`/`--fail-on-eol`) is adopted in production, ~180 days after each release's registry stamp the tier-1 provenance goes stale and the freshness precondition self-degrades EVERY gated scan to `indeterminate`/exit-1 regardless of the project (the intended fail-closed direction — never a false-green — but a fleet-wide false-RED if the bundled registry is not re-stamped). Worth a release-time registry re-stamp checklist item, a longer bundled-tier max-age, or a bundled-registry refresh path — a cross-axis staleness-defaults concern, not fixable inside this story's boundaries.
  evidence: `currency.py:_REGISTRY_MAX_AGE_DAYS = 180` + `_registry_feed_provenance` derive staleness from the registry's own `updated:` field against wall-clock `now`; `engines.CurrencyEngine.run` appends `currency_stale_finding` whenever `self._gating and (currency_data is None or not currency_data.max_age_ok)`. The registry is a pre-existing 6.3 bundled resource (no writer/refresh script exists, only the manual CFE-source re-copy); 6.5 only makes its staleness gate-relevant. Two conformance tests that compared gated-vs-unconfigured findings against the live registry were made time-robust this pass (they now exclude the gate-only `indeterminate:currency-registry-*` provenance id from the producer-invariance comparison), but the underlying operational aging is not a test artifact. Raised by the Blind Hunter review pass (fail-closed, medium).

  status: open

  verified: 2026-07-30 — `data/lts-registry.yaml:35` still carries the fixed `updated: 2026-07-06` — 24 days stale as of this check.
## Deferred from: follow-up code review of spec-6-5-two-mode-policy-integration (2026-07-24, bmad-dev-auto follow-up review pass)

## DW-6-5-2 — The `warn-as-error` exit projection leaves no trace anywhere in the output — the report persists…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-5-two-mode-policy-integration.md`
  summary: The `warn-as-error` exit projection leaves no trace anywhere in the output — the report persists `status: warn` alongside `exit_code: 1` with nothing (no report field, no text-render line, no stderr note) explaining the divergence, unlike `--warn-only` (which gets a dedicated FR19 graduate-to-enforcing render nudge) and unlike the gating booleans (surfaced via `AxisCoverage.gating` per FR37). A repo that sets `warn-as-error = true` in TOML reds a teammate's CI with an empty stderr and a report whose findings are all warn-level; a JSON consumer that re-derives exit from status disagrees with the recorded `exit_code`. The frozen schema bars a new report field (post-6.1 no-schema-widening rule), so the fix is a render/stderr transparency line or a deliberate schema amendment — an exit-code-provenance design decision, not a review-pass patch.
  evidence: `report.assemble_report` threads `warn_as_error` ONLY into `exit_code_for(warn_is_error=…)`; `render_text` has the `--warn-only` nudge (report.py) but no warn-as-error counterpart. Raised independently by BOTH the Blind Hunter and the Edge Case Hunter this pass. Pre-existing angle: `verdict.exit_code_for`'s `warn_is_error` knob shipped (tested) in 1.1/1.2 with no surfaced provenance; 6.5 only made it CLI/TOML-reachable.

  status: open

## DW-6-5-3 — Under an active gate with an absent/stale feed, `CurrencyEngine.run` (deliberately mirroring `Os…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-5-two-mode-policy-integration.md`
  summary: Under an active gate with an absent/stale feed, `CurrencyEngine.run` (deliberately mirroring `OsvEngine._kev_enrichment`, per the 6.5 intent contract) still reports `deps_assessed == deps_total` in `AxisCoverage` while appending the whole-axis `indeterminate` provenance finding — so an FR37-style coverage consumer renders 100% assessed (green) for an axis the very same report declares untrustworthy. Cross-axis by construction (the 6.4 KEV path has the identical shape); fixing currency alone would desync the two mirrors, so this needs a deliberate cross-axis coverage-semantics decision (e.g. an assessed-vs-trusted split or a provenance-degraded marker) in a future pass.
  evidence: `engines.CurrencyEngine.run` sets `deps_assessed=inventory.count` unconditionally before the gated `currency_stale_finding` append; `_kev_enrichment` is the shipped precedent 6.5 was contractually required to mirror ("exactly as `_kev_enrichment` gates on `fail_on_kev`"). Raised by the Blind Hunter review pass; internally coherent with 6.4, but 6.5 is the story that made the dissonance reachable on a second axis.

  status: open
## Deferred from: code review of spec-6-7-epss-feed-the-min-epss-gate (2026-07-24, Blind Hunter + Edge Case Hunter)

## DW-6-7-1 — `OsvParse.kev_candidates` (the finding.id -> CVE-alias-tuple mapping populated at OSV-parse time…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-7-epss-feed-the-min-epss-gate.md`
  summary: `OsvParse.kev_candidates` (the finding.id -> CVE-alias-tuple mapping populated at OSV-parse time) is named for its original, KEV-exclusive purpose, but Story 6.7 now feeds the SAME collection into EPSS matching too (`_stamp_epss(..., parse.kev_candidates)`) — it is now generically "the per-finding CVE candidate set any feed enrichment matches against," not KEV-specific data, and the name no longer reflects that. A future third feed consumer would compound the confusion. Renaming it (e.g. to `advisory_candidates`) touches call sites in both the KEV (6.4) and EPSS (6.7) paths, which is a naming-only refactor across two already-shipped/shipping stories, not a single-story patch.
  evidence: `vuln.py`'s `OsvParse.kev_candidates` field (Story 6.4) is read verbatim by both `engines._stamp_kev` and the new `engines._stamp_epss` (Story 6.7's Boundaries explicitly mandate this reuse — "no new candidate-collection mechanism"). Raised by the Blind Hunter review pass (naming/maintainability, not a behavior defect).

  status: open

## DW-6-7-2 — The EPSS cache reuses `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (7 days) unchanged — the same shared con…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-7-epss-feed-the-min-epss-gate.md`
  summary: The EPSS cache reuses `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (7 days) unchanged — the same shared constant KEV and endoflife.date use — without reconsidering whether it fits EPSS's own publication cadence. FIRST.org republishes EPSS scores daily and a CVE's score can shift materially within days of active exploitation, so a week-old cached score is treated as fully "fresh" for the entire week; this is arguably the best-fit feed of the three for the existing default (a daily feed, a 7-day ceiling), but the fit was never deliberately evaluated — it was inherited because Story 6.7's boundaries forbid new staleness logic ("`feeds.py` owns cache location/lifecycle/staleness math... no new cache-root or staleness logic"). Same underlying tuning question already ledgered for the endoflife.date feed above; a cross-feed staleness-defaults pass could address both at once.
  evidence: `feeds.py`'s `_epss_enrichment`/`epss_cache_path` reuse `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (7) with no EPSS-specific override; no code path in this diff computes or considers EPSS's real-world update frequency. Raised by the Blind Hunter review pass (product/tuning, not a code defect).

  status: open

  verified: 2026-07-30 — No EPSS-specific max-age constant exists; the EPSS path still resolves through `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (`feeds.py:98`).
## Deferred from: follow-up code review of spec-6-7-epss-feed-the-min-epss-gate (2026-07-24, bmad-dev-auto follow-up review pass)

## DW-6-7-3 — The real FIRST.org EPSS feed (~290k rows, republished daily) was poured into cache conventions s…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-7-epss-feed-the-min-epss-gate.md`
  summary: The real FIRST.org EPSS feed (~290k rows, republished daily) was poured into cache conventions sized for KEV's ~1.3k entries with no recorded size consideration — `write_epss_cache` pretty-prints with `indent=2, sort_keys=True` (roughly doubling a multi-tens-of-MB cache file), every `OsvEngine.run` re-reads and `json.loads` the ENTIRE document into a ~290k-entry dict even for a 3-dependency scan, and `refresh_epss_feed.py` simultaneously buffers the raw gzip, the full decompressed string, a `splitlines()` list, and the normalized score list (~100MB+ peak). Nothing misbehaves at toy-fixture scale — which is exactly the only scale the test suite exercises — so a real-feed performance/footprint evaluation (compact separators, streaming parse, or a per-run parsed-catalog cache) needs its own deliberate pass; changing only the EPSS copy also diverges from the shared write-shape the KEV/endoflife siblings establish.
  evidence: KEV's shipped catalog is ~1.3k entries vs EPSS's ~290k published rows; `feeds.write_epss_cache` mirrors `write_kev_cache`'s `indent=2, sort_keys=True` verbatim (spec boundary: "siblings of the KEV trio, same shape"); `engines._epss_enrichment` calls `feeds.load_epss_scores(path)` unconditionally per run with no memoization. Raised by the follow-up Blind Hunter pass (real-feed performance regression invisible to the suite).

  status: open

## DW-6-7-4 — The `feeds.py` atomic-write shape now carries FOUR copies of a latent double-close: if `json.dum…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-7-epss-feed-the-min-epss-gate.md`
  summary: The `feeds.py` atomic-write shape now carries FOUR copies of a latent double-close: if `json.dump` raises inside the `with os.fdopen(handle, ...)` block, the context manager closes the fd, then the `except BaseException` handler calls `os.close(handle)` a second time — normally a swallowed EBADF, but in any threaded embedder that fd number may already have been reused, silently closing a stranger's file descriptor. `write_epss_cache` (Story 6.7) is the newest copy, deliberately mirroring `write_kev_cache`/`write_endoflife_cache` "verbatim" per its spec boundary; the unified fix (an fh-opened flag, or closing only pre-fdopen) spans the KEV and endoflife writers that 6.7's own Never-list forbids touching, so it needs a dedicated cross-feed pass.
  evidence: `feeds.py`'s three `write_*_cache` functions (KEV, endoflife, EPSS) share the identical `except BaseException: os.close(handle)` recovery after an `os.fdopen` context manager that already owns (and closes) the same handle; `os.fdopen` docs — the file object takes ownership of the fd. Raised independently by both the follow-up Blind Hunter and Edge Case Hunter passes (latent, unreproducible-when-it-fires class).

  status: done 2026-07-30

  verified: 2026-07-30 — ALREADY RESOLVED. All three atomic-write sites (`feeds.py:257-260`, `:322-325`, `:410-413`) now wrap `os.close(handle)` in `try/except OSError: pass`, with a comment stating the intent — 'tolerate EBADF rather than double-close'. The latent double-close is defused at every site; the entry's 'four copies' is now three, all guarded.

## DW-6-7-5 — The conformance-suite helper trio is now duplicated wholesale across feed-enrichment test files…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-7-epss-feed-the-min-epss-gate.md`
  summary: The conformance-suite helper trio is now duplicated wholesale across feed-enrichment test files — `run_scan`/`parse_report` exist verbatim in three files and `load_schema` in four (`test_scan_harness.py`, `test_kev_enrichment.py`, `test_report_schema.py`, `test_epss_enrichment.py`), plus re-copied `_osv_scanner_bin`/`_load_osv_builder`/fixture constants from `test_kev_enrichment.py` — every copy is a future drift site (a schema-path or CLI-invocation change now needs four synchronized edits). Consolidating into a shared `tests/conformance/conftest.py` (or helpers module) touches the pre-existing 1.x/6.4 test files outside any single story's diff, so it needs its own test-infrastructure pass.
  evidence: `grep -l "def run_scan" tests/conformance/` matches test_scan_harness.py, test_kev_enrichment.py, and test_epss_enrichment.py; `def load_schema` additionally in test_report_schema.py; Story 6.7's file re-copies were spec-directed ("mirrors test_kev_enrichment.py's 10-test structure"). Raised by the follow-up Blind Hunter pass (maintainability, not behavior).

  status: open
## Deferred from: code review of spec-6-8-baseline-grandfathering (2026-07-24, bmad-dev-auto review pass)

## DW-6-8-1 — `architecture.md`'s "Project Structure" tree (§ around the `waiver.py`/`report.py`/`verdict.py`…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-8-baseline-grandfathering.md`
  summary: `architecture.md`'s "Project Structure" tree (§ around the `waiver.py`/`report.py`/`verdict.py` entries) is stale for the whole of Epic 6 — it lists none of `license.py`, `currency.py`, `feeds.py`, `actuator.py`, or the FR39 baseline addition to `waiver.py`, even though 6.2/6.3/6.4/6.7/6.8 have all now shipped. This story's own review corrected the (separate) "Module structure" list and the F8/FR39 prose bullets to reflect the single-module `waiver.py` design (see the same file's Architectural-deltas section, corrected 2026-07-24), but the older "Project Structure" tree was already out of date before this story and stayed out of date after it — a full Epic-6 reconciliation of that specific tree is out of this story's scope.
  evidence: `_bmad-output/planning-artifacts/architecture.md`'s "Project Structure" tree (the block containing `waiver.py               # FR24-26 — .yaml read (safe_load) + --bypass stanza (safe_dump)`) has no sibling entries for any Epic 6 module; the separate "Module structure" list a few hundred lines earlier in the same file DOES track them (and was corrected by this review pass for the baseline/waiver consolidation). Raised by the Blind Hunter review pass (documentation drift, not a code defect).

  status: open
## Deferred from: follow-up code review of spec-6-8-baseline-grandfathering (2026-07-24, bmad-dev-auto follow-up review pass)

## DW-6-8-2 — `--baseline-emit` stamps every proposed entry with `expires_at = now + waiver_default_expiry_day…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-8-baseline-grandfathering.md`
  summary: `--baseline-emit` stamps every proposed entry with `expires_at = now + waiver_default_expiry_days` (default 14) — the WAIVER lifecycle's short-leash default reused unexamined for the baseline's different lifecycle (bulk adoption-time debt vs an individually-signed short-term exception), so a team that commits the emitted file unedited has its entire grandfathered set expire simultaneously two weeks after adoption. The dates are visible in the emitted YAML and the human owns the file (this pass patched the help text to disclose the stamping), but whether baselines deserve their own, longer default (a `baseline_default_expiry_days` config key or `--baseline-emit`-side knob) is a product decision no story has made — the 6.8 spec resolved emit behavior purely by mirroring `emit_bypass_stanza`.
  evidence: `cli.py`'s `--baseline-emit` block calls `emit_baseline_stanza(rungs, now=now, expiry_days=config.waiver_default_expiry_days)`; `config.py` defines `waiver_default_expiry_days: int = 14` with no baseline-specific sibling; the 6.8 review pass added the disclosure to the flag's help text but deliberately did not invent a new config surface. Raised by the follow-up Blind Hunter pass (lifecycle/product tuning, not a code defect).

  status: open

  verified: 2026-07-30 — `cli.py:686` still documents the stamp as `expires_at = now + waiver_default_expiry_days`; behaviour unchanged.

## DW-6-8-3 — An EXPIRED suppression (waiver or baseline) is invisible in the machine-readable contract: `supp…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-8-baseline-grandfathering.md`
  summary: An EXPIRED suppression (waiver or baseline) is invisible in the machine-readable contract: `suppressions[]` carries applied entries only, and the `[waiver-expired]`/`[baseline-expired]` notices exist solely in `render_text`'s free-text output — so a `--format json` CI consumer cannot distinguish "a new finding appeared" from "a previously-suppressed finding re-blocked because its entry expired." Pre-existing shape from Story 3.3/6.1 (expired waivers were already text-only); Story 6.8 widens the blast radius (a whole grandfathered set can expire at once) but is spec-barred from touching `report-schema.json`/`models.py` ("no 6.x producer story may widen the schema"), so a schema-level `expired_suppressions[]` (or equivalent) needs a dedicated schema-versioned pass covering both origins at once.
  evidence: `report.py` threads `expired_waivers`/`expired_baseline` into `render_text` only; `assemble_report`/`ComplianceReport` accept no expired-notice input; `report-schema.json` has no expired-suppression slot anywhere; conformance test `test_expired_baseline_entry_reblocks_the_finding` shows the JSON document with `suppressions=[]` and no other machine-readable trace. Raised by the follow-up Blind Hunter pass (observability gap in the primary CI surface).

  status: open

  verified: 2026-07-30 — Neither `models.py` nor `data/report-schema.json` contains any `expired` handling — an expired suppression is still invisible in the machine-readable contract.

## DW-6-8-4 — `report-schema.json`'s top-level `suppressions` description (the `"description"` string on the `…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-8-baseline-grandfathering.md`
  summary: `report-schema.json`'s top-level `suppressions` description (the `"description"` string on the `suppressions` array property, ~line 150) still reads "Story 6.1 populates only the waiver half" — factually stale now that Story 6.8 ships the `origin="baseline"` producer, and self-contradicting within the same file (the `suppressedFinding` def's own description at ~line 551 already says "Story 6.8 the baseline half"). A one-string description fix, but the 6.8 spec froze `report-schema.json` as UNTOUCHED, so it belongs to whichever next story (or maintenance pass) is allowed to touch the schema file.
  evidence: `src/pyforge/warden/data/report-schema.json` line ~150: "Story 6.1 populates only the waiver half; absent/[] on a scan with no applied waivers." vs line ~551's suppressedFinding description: "(Story 6.1 wires the waiver half; Story 6.8 the baseline half)". The file is absent from the 6.8 diff (spec Always-constraint: "models.py/report-schema.json are UNTOUCHED"). Raised by the follow-up Blind Hunter pass (stale contract prose, no behavioral impact — descriptions are non-normative).

  status: open

## DW-6-8-5 — `load_waivers` still parses with plain `yaml.safe_load`, which silently keeps the LAST of two du…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-6-8-baseline-grandfathering.md`
  summary: `load_waivers` still parses with plain `yaml.safe_load`, which silently keeps the LAST of two duplicate mapping keys — two `waivers:` sections in one `.warden-waivers.yaml` (or a duplicated field inside one entry) silently drop the earlier occurrence before `_validate_document`'s duplicate-*id* check can see it. The 6.8 follow-up review fixed exactly this for the BASELINE loader (`_UniqueKeySafeLoader`, a SafeLoader restriction that raises on duplicate keys), but the 6.8 spec's Never-list forbids any edit to `load_waivers`/the waiver-only path, so extending the same loader to the waiver side needs its own small pass (fail direction is closed — dropped entries re-gate rather than suppress — which is why this is deferred, not urgent).
  evidence: `waiver.py`'s `load_waivers` uses `yaml.safe_load(handle)` directly; `_UniqueKeySafeLoader` (added by the 6.8 follow-up review) is wired into `load_baseline` only, with its docstring explicitly recording "load_waivers deliberately keeps stock yaml.safe_load (this story may not alter the waiver-only path)". Confirmed empirically by the Edge Case Hunter pass (PyYAML last-wins on duplicate keys, both loaders affected pre-fix).

  status: open

  verified: 2026-07-30 — `waiver.py:508-520` still parses with plain `yaml.safe_load` and its own docstring reaffirms safe_load-only; no duplicate-key guard was added.
## Deferred from: code review of spec-5-1-actionable-diagnostics-safe-by-default-posture (2026-07-24, Blind Hunter + Edge Case Hunter)

## DW-5-1-1 — A hygiene-axis remediation line's manifest+location clause is frequently unavailable because `hy…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-1-actionable-diagnostics-safe-by-default-posture.md`
  summary: A hygiene-axis remediation line's manifest+location clause is frequently unavailable because `hygiene.py`'s `_record_to_finding` sets `Finding.subject` to deptry's raw import-module name (e.g. `yaml`, `bs4`, `PIL`, `sklearn`), not the declaring distribution/component name — and this codebase has no existing correlation table from an import name back to a component. `render_text`'s manifest-location lookup (keyed by component name, now also by `pypi_identity.name`) simply omits the clause for these cases, which is spec-compliant (AC1 says "(when known)") but leaves the location half of AC1's promise silently absent for a large share of real-world hygiene findings. A real fix needs an import-name→distribution mapping, which is a substantially larger effort (adjacent to `mapping.py`'s domain) than this story's scope.
  evidence: `hygiene.py:543` sets `subject=module` (the raw deptry-reported import name); the module's own docstring (lines ~17-22) already documents that a module name is "not a distribution name" and cites real examples (PyYAML→yaml, beautifulsoup4→bs4, Pillow→PIL, scikit-learn→sklearn). Raised by the Blind Hunter review pass.
  status: open

## DW-5-1-2 — `--doctor` silently no-ops every other `scan` flag it's combined with (`--sbom-output`, `--basel…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-1-actionable-diagnostics-safe-by-default-posture.md`
  summary: `--doctor` silently no-ops every other `scan` flag it's combined with (`--sbom-output`, `--baseline`, `--fail-on`, `--allow-licenses`/`--deny-licenses`, `--warn-only`, `--open-fix-prs`/`--fix-prs-dry-run`, etc.) since `_run_doctor` dispatches before any of them are read, with no warning that they were ignored. Low-priority UX polish (no incorrect security/policy behavior results — the flags are simply never consulted), not a functional defect; a future story could add a stderr note when `--doctor` coexists with a policy-affecting flag.
  evidence: `main()`'s `if args.doctor: return _run_doctor(args)` branch (cli.py) precedes `return _run_scan(args)` unconditionally; `_run_doctor` never reads any flag other than `args.path`/`args.format`. Raised by the Blind Hunter review pass.
  status: open
  verified: 2026-07-30 — `cli.py:258` still returns `_run_doctor(args)` strictly before the scan path, so every other `scan` flag is still silently no-op'd when `--doctor` is passed.

## DW-5-1-3 — `report._remediation_line`'s vuln branch recovers the advisory id for display by re-splitting th…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-1-actionable-diagnostics-safe-by-default-posture.md`
  summary: `report._remediation_line`'s vuln branch recovers the advisory id for display by re-splitting the finding id (`finding_id.split(":", 2)[1]`), which is already percent-escaped (`_sanitize_id_segment` ran when the id was constructed in `vuln.py`) rather than the raw advisory id available at `Finding`-construction time. A grammar-legal advisory id containing a colon or newline would render its escaped form (e.g. `%3A`) in the human-facing remediation text. Practically unreachable — every real-world advisory id format (GHSA-/CVE-/PYSEC-) never contains a colon or newline — so deferred rather than patched now; a real fix needs either threading the raw advisory id through a second render_text-only side channel or a correct reverse-`_sanitize_id_segment` unescaper.
  evidence: `report.py`'s `_remediation_line` vuln branch splits `finding["id"]` to recover the advisory-id display segment; `vuln.py`'s `_sanitize_id_segment` (via `interfaces._sanitize_id_segment`) already ran on that segment when the id was built. Raised by the Blind Hunter review pass.
  status: open

## DW-5-1-4 — `tests/conftest.py`'s comment describing the ambient offline OSV DB fixture still claims "its ON…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-1-actionable-diagnostics-safe-by-default-posture.md`
  summary: `tests/conftest.py`'s comment describing the ambient offline OSV DB fixture still claims "its ONE seeded advisory (`PDOS-FIXTURE-0001`, package `pdos-vuln-fixture`)" — already stale before this story (a `PDOS-FIXTURE-0002` record already existed), and this story's own new `PDOS-FIXTURE-0003` fixture (added for fixed-version extraction coverage) compounds the inaccuracy further. Pre-existing documentation drift, not caused by this story; a one-line comment fix whenever `conftest.py` is next touched.
  evidence: `tests/conftest.py` (~line 277-279) vs `tests/fixtures/osv-db/pypi/` containing `PDOS-FIXTURE-0001.json`, `PDOS-FIXTURE-0002.json`, and (as of this story) `PDOS-FIXTURE-0003.json`. Raised by the Blind Hunter review pass.
  status: open

## DW-5-1-5 — The literal argv `["deptry", "--version"]` / `["osv-scanner", "--version"]` now exists independe…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-1-actionable-diagnostics-safe-by-default-posture.md`
  summary: The literal argv `["deptry", "--version"]` / `["osv-scanner", "--version"]` now exists independently at three call sites (`DeptryEngine.run`'s own pre-flight, `OsvEngine.run`'s own pre-flight, and the new `run_doctor_checks`) with no shared constant — a future rename or flag change to either pre-flight invocation has to be applied at all three by hand. Pre-existing duplication pattern between the two engines' own pre-flights (Story 6.6) that this story's doctor aggregation extends to a third site rather than introduces fresh; low value to fix in isolation without also touching the two already-shipped, already-tested engine call sites.
  evidence: `engines.py` — `DeptryEngine.run`'s pre-flight, `OsvEngine.run`'s pre-flight, and the new `run_doctor_checks` each declare the same two argv literals locally. Raised by the Blind Hunter review pass.

  status: open

  verified: 2026-07-30 — The literal argv still exists at FOUR sites: `engines.py:725`, `:732`, `:947`, `:1485`.
## Deferred from: follow-up code review of spec-5-1-actionable-diagnostics-safe-by-default-posture (2026-07-24, bmad-dev-auto follow-up review pass)

## DW-5-1-6 — `vuln._extract_fixed_version` takes the FIRST well-formed `fixed` event in document order (an in…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-1-actionable-diagnostics-safe-by-default-posture.md`
  summary: `vuln._extract_fixed_version` takes the FIRST well-formed `fixed` event in document order (an intent-contract-recorded design decision), which for real multi-branch backport advisories (Django/DRF/cryptography-style — one `affected[]` entry or range per release series, oldest branch listed first) typically yields the OLDEST branch's fix, so the remediation line can advise "upgrade django to >= 3.2.20 to resolve GHSA-…" to a user whose installed 4.2.1 already satisfies that bound — self-contradictory, unactionable advice. Taking the MAX well-formed fixed event instead would be universally sufficient (upgrading to the highest fixed version always resolves the advisory) at identical cost and still without any semver-range resolution — but "take the FIRST well-formed fixed event" is written inside the spec's intent contract (Block If), so changing the selection rule needs a spec-level decision, not a review patch.
  evidence: `vuln.py`'s `_extract_fixed_version` returns on the first `isinstance(fixed, str) and fixed` hit across `affected[].ranges[].events[]` in document order; the 5.1 spec's Block If section records "take the FIRST well-formed fixed event found for that advisory … do not build a full semver-range resolver". Both the initial Blind Hunter pass's wording concern ("to resolve" overclaims sufficiency) and this follow-up pass's oldest-branch scenario describe the same selection-rule root cause. Raised by the follow-up Blind Hunter pass.
  status: open
  verified: 2026-07-30 — `vuln.py:744-750` — `_extract_fixed_version`'s own docstring still specifies the FIRST well-formed `fixed` event in document order.

## DW-5-1-7 — The remediation line's manifest-location clause unions provenance across ALL same-named componen…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-1-actionable-diagnostics-safe-by-default-posture.md`
  summary: The remediation line's manifest-location clause unions provenance across ALL same-named components regardless of version (the first review pass's deliberate anti-clobber fix), so a version-bearing finding (`vuln:GHSA-x:foo@1.0.0`) on a project declaring `foo==1.0.0` only in `requirements.txt` and `foo==2.0.0` in `pixi.toml` renders "declared in pixi.toml [dependencies]; requirements.txt [requirements]" — listing a manifest that declares only the NON-vulnerable version, steering the operator to edit the wrong file. Version-aware keying (name@version when the finding subject carries a version, falling back to the name union otherwise) would restore precision; it needs per-id-family subject parsing and care not to regress the name-only families (hygiene/license/currency/indeterminate), so it is a contained follow-up rather than a review patch.
  evidence: `cli.py`'s `manifest_locations` build unions `component.provenance` per canonicalized name with no version key; `inventory.py` documents that distinct versions of one name stay distinct components, each with its own provenance. Raised by the follow-up Blind Hunter pass.

  status: open
## Deferred from: second follow-up code review of spec-5-1-actionable-diagnostics-safe-by-default-posture (2026-07-24, bmad-dev-auto third review pass)

## DW-5-1-8 — The `manifest_locations` lookup applies PEP-503 canonicalization (`_canonical_subject_key`) to E…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-1-actionable-diagnostics-safe-by-default-posture.md`
  summary: The `manifest_locations` lookup applies PEP-503 canonicalization (`_canonical_subject_key`) to EVERY component name, but the collapse is only semantically valid in the PyPI namespace — conda treats separator-twins (`importlib-metadata` vs `importlib_metadata`, both real distinct conda-forge packages) as different packages, so an environment declaring both merges their declaration sites under one canonical key and a remediation line for either can name the other's manifest location. A correct fix needs an exact-match-first lookup (raw component-name keys tried before the canonical fallback), which reshapes the single-`Mapping` seam `render_text(manifest_locations=...)` currently carries into a two-tier lookup — a contained follow-up, not a review patch, and low consequence (an extra location listed for what is almost always the same upstream project renamed).
  evidence: `cli.py`'s `manifest_locations` build canonicalizes `component.name` unconditionally (`keys = [_canonical_subject_key(component.name)]`) and unions provenance on key collision; `report._canonical_subject_key`'s own docstring justification ("two spellings that collapse together ARE the same PyPI package") holds only for PyPI-namespace names, while the dict is also keyed by conda-native `component.name` for conda/pixi-sourced components. Raised independently by both the Blind Hunter and Edge Case Hunter of the third review pass.

  status: open
### DW-FU-5-1: Follow-up review still recommended for 5-1-actionable-diagnostics-safe-by-default-posture after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-5-1-actionable-diagnostics-safe-by-default-posture.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 1) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260724-162245-3440; this entry preserves the lingering recommendation for a deliberate later review.
status: open

## Deferred from: code review of spec-5-2-fleet-scale-validation-corpus-oracle-maturation (2026-07-24, bmad-dev-auto review pass)

## DW-5-2-1 — The new `ThreadPoolExecutor`-based 4-axis engine fan-out in `cli.py`'s `_run_scan` changes SIGIN…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-2-fleet-scale-validation-corpus-oracle-maturation.md`
  summary: The new `ThreadPoolExecutor`-based 4-axis engine fan-out in `cli.py`'s `_run_scan` changes SIGINT latency versus the pre-5.2 sequential loop — `with ThreadPoolExecutor(...) as pool:`'s `__exit__` unconditionally calls `shutdown(wait=True)`, so a `KeyboardInterrupt` raised while `future.result()` is blocked must wait for every already-started engine (including any in-flight deptry/osv-scanner subprocess) to finish before it can propagate, whereas the old loop had at most one engine in flight at a time.
  evidence: `concurrent.futures.Executor.__exit__` hardcodes `self.shutdown(wait=True)`, not parameterizable via the context-manager form; fixing this correctly needs manual `pool.shutdown(wait=False, cancel_futures=True)` handling in an except-path around `future.result()`, which touches interrupt-sensitive code (this project already has an explicit top-level `except KeyboardInterrupt`/exit-130 contract in `main()`) — a deliberate, focused change rather than a same-pass patch. Raised independently by both the Blind Hunter and Edge Case Hunter of the Story 5.2 review pass.
  status: open

## DW-5-2-2 — `test_extraction_oracle.py`'s corpus-scale comparison excludes any manifest whose raw text match…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-2-fleet-scale-validation-corpus-oracle-maturation.md`
  summary: `test_extraction_oracle.py`'s corpus-scale comparison excludes any manifest whose raw text matches `_EXCLUDED_CONSTRUCT_RE` (`compiler(`/`stdlib(`/`pin_subpackage(`) via a plain substring search over the WHOLE file, not parsed structure — a file that merely mentions one of those strings in a comment or a string literal (e.g. an `about.summary` describing "wraps stdlib(json)") is needlessly excluded from the strict per-file comparison, silently and unmeasurably reducing oracle coverage.
  evidence: `_EXCLUDED_CONSTRUCT_RE.search(text)` runs against the full file text read from disk, not against parsed YAML values; conservative in direction (under-compares rather than mis-compares) so it is safety-neutral, not a correctness bug, but a structural (AST-aware) exclusion would be more precise. Raised by the Blind Hunter of the Story 5.2 review pass.
  status: open

## DW-5-2-3 — `scripts/harvest_corpus.py`'s `write_sources_md` hardcodes the 3-bullet "Hand-authored" descript…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-2-fleet-scale-validation-corpus-oracle-maturation.md`
  summary: `scripts/harvest_corpus.py`'s `write_sources_md` hardcodes the 3-bullet "Hand-authored" description list in prose rather than deriving it from `_HANDAUTHORED_FIXTURES`, so adding/renaming/removing an entry in that dict silently leaves `SOURCES.md`'s prose out of sync with what is actually on disk (the `handauthored` parameter passed into the function is unused, deliberately `del`'d).
  evidence: `write_sources_md`'s hand-authored section is a fixed `lines` literal, unlike its own upstream half (`upstream_lines`, derived live from `_UPSTREAM_OUT.iterdir()`); making the two symmetric needs each `_HANDAUTHORED_FIXTURES` entry to carry a human-readable description alongside its content, a moderate refactor of a dev-only maintenance script. Raised by the Blind Hunter of the Story 5.2 review pass.
  status: open

## DW-5-2-4 — `test_perf_overhead.py`'s `REPRESENTATIVE_TARGET` hardcodes a single corpus feedstock path (`rec…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-2-fleet-scale-validation-corpus-oracle-maturation.md`
  summary: `test_perf_overhead.py`'s `REPRESENTATIVE_TARGET` hardcodes a single corpus feedstock path (`recipes/types-lxml`); since `harvest_corpus.py`'s `harvest_recipes()` wipes and fully re-derives the corpus from the live `recipes/` tree on every re-run, a future re-harvest that happens to occur after that specific feedstock is removed upstream would make the test's own "run scripts/harvest_corpus.py" failure-message remedy actively wrong (re-harvesting cannot restore a recipe no longer present in `recipes/`).
  evidence: `test_perf_overhead.py` references the literal path once, with no fallback/discovery logic if it is absent; low likelihood (an established, actively-maintained feedstock) and low consequence (a loud, clearly-worded test failure rather than a silent gap) but a real edge case. Raised by the Edge Case Hunter of the Story 5.2 review pass.

  status: open
## Deferred from: follow-up code review of spec-5-2-fleet-scale-validation-corpus-oracle-maturation (2026-07-24, bmad-dev-auto follow-up review pass)

## DW-5-2-5 — No CI workflow or scheduled runner ever executes the new `pyforge-warden-test-corpus-oracle` pix…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-2-fleet-scale-validation-corpus-oracle-maturation.md`
  summary: No CI workflow or scheduled runner ever executes the new `pyforge-warden-test-corpus-oracle` pixi task (`-m slow`), and Story 5.2's whole-module slow-marking moved the 4 pre-existing precision differential-oracle tests (Stories 2.2/2.3) out of the default `pyforge-warden-test` loop with it — so an extractor change that breaks render-parity on the precision fixtures now merges green through the default gate and only surfaces whenever someone manually remembers to run the slow task, far from the offending commit.
  evidence: A sweep of `.github/workflows/` shows no workflow references any pyforge-warden pixi task (pre-existing — the default task was never CI-wired either, but it IS the loop's canonical verify command, which the slow task is not); `pixi.toml`'s `pyforge-warden-test` now carries `-m "not slow"` and `test_extraction_oracle.py` is module-marked slow per the spec's own recorded deviation. Fixing needs repo-level CI/scheduler wiring (out of the story's package scope). Raised by the follow-up Blind Hunter pass.
  status: open
  verified: 2026-07-30 — No file under `.github/workflows/` references the corpus-oracle or corpus-test task — nothing schedules or gates it.

## DW-5-2-6 — `.warden-baseline.yaml`'s first entry hardcodes the running interpreter's patch version in its f…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-2-fleet-scale-validation-corpus-oracle-maturation.md`
  summary: `.warden-baseline.yaml`'s first entry hardcodes the running interpreter's patch version in its finding id (`currency:unknown:!python-runtime@3.14.6`), so any pixi-environment Python bump silently un-matches it — the finding resurfaces un-grandfathered as report noise (an unbypassed WARN; exit 0 is unaffected since WARN never gates) while the stale entry sits dead in the committed file until the next regeneration.
  evidence: `currency.py` builds the id from `sys.version_info[:3]`; the test suite is insulated only because `tests/conftest.py` writes its ambient endoflife feed with the dynamically-computed interpreter version, whereas the committed baseline froze the opposite, brittle strategy. A version-agnostic baseline id would need a Story 6.8 match-semantics change (out of 5.2's validation-only scope). Raised independently by both reviewers of the follow-up pass.
  status: open
  verified: 2026-07-30 — `.warden-baseline.yaml:38` still pins the running interpreter's patch version: `currency:unknown:!python-runtime@3.14.6`.

## DW-5-2-7 — All 19 entries in the committed `.warden-baseline.yaml` expire simultaneously at 2027-07-24T00:0…

- source_spec: `_bmad-output/projects/pyforge-warden/implementation-artifacts/spec-5-2-fleet-scale-validation-corpus-oracle-maturation.md`
  summary: All 19 entries in the committed `.warden-baseline.yaml` expire simultaneously at 2027-07-24T00:00:00Z, so on that date the default-suite dogfood test (`test_dogfood.py`'s clean-state half, not slow-marked) and the `pyforge-warden-dogfood` pixi task both go red by calendar with no code change — an unattended loop would triage it as a code regression. The follow-up review pass documented the event and the correct regeneration command (`python scripts/dogfood_scan.py --emit-baseline`) in the baseline file's own header, but the simultaneous-expiry red-day itself remains scheduled; staggering or deliberately re-stamping expiries ahead of the date is the remaining work.
  evidence: `waiver.py` treats an expired exact-id match as unmatched (rung left blocking, expired-notice collected) and `verdict.py` maps INDETERMINATE to exit 1; the six `indeterminate:no-version:*` findings fire in the test environment too, so the failure is deterministic once the wall clock passes the shared expires_at. Expiry-forces-re-review is Story 6.8's intended design — the defect is only the single shared cliff date. Raised independently by both reviewers of the follow-up pass.

  status: open

  verified: 2026-07-30 — Confirmed exactly: all 19 entries carry `expires_at: "2027-07-24T00:00:00+00:00"`, and the file's own note at line 31 records the simultaneity.
## Deferred: upstream bug report — pixi-build-python path panic (2026-07-25)

## DW-CROSS-CUTTING-1 — `pixi-build-python` 0.8.3 panics with an unsigned byte-index underflow (`tools.rs:461`, `end byt…

- source_spec: cross-cutting (harness; Marshal station)
  summary: `pixi-build-python` 0.8.3 panics with an unsigned byte-index underflow (`tools.rs:461`, `end byte index 18446744073709551608 is out of bounds for string of length 260`) on any source-package build whose `workDirectory` path is long enough — measured 149-char root OK / 162-char root panics; today's failures had ~238-char workDirectories. **A full upstream-ready report is written and tracked at `_bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-report-pixi-build-python-path-panic.md` — deliberately NOT filed (operator decision 2026-07-25); submit verbatim when we choose to.** Nothing to pin to: our backend spec is already `version = "0.*"` and conda-forge's newest IS 0.8.3, so a fix lands automatically once published.
  mitigations shipped: (1) `--frozen` on every build line's `[verify]`; (2) loop homes relocated to a short root `~/.bmad-loops/<slug>` via `scripts/bmad-loop-worktree` (`BMAD_LOOP_HOME_ROOT` overrides) — worst-case workDirectory 238 → 192 chars; (3) new-environment lock bootstrap from the short main checkout before a loop line runs frozen.
  related hazard: a *successful* unfrozen re-solve inside a worktree rewrites `pixi.lock` with worktree-absolute `file://` channel paths — toxic to commit via the loop's `git add -A`. Also in the report.
  status: open
