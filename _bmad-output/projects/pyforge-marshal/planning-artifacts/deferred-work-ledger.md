---
doc_type: deferred-work-ledger
project: pyforge-marshal
date: 2026-07-29
status: promoted-verbatim
---

# pyforge-marshal — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-29 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown, and this repo has already lost data that way
(pyforge-atlas's live ledger is still truncated to 11 of 64 entries, collateral of the
2026-07-19 copy failure). Until today this project had **no tracked ledger at all**, so
its entire deferred-work record — 4 KB — existed only in
scratch space. Found by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current. The one intentional edit is
id renaming, below.

Durability first; curation is owned follow-up work.

## Ids renamed on promotion

- `DW-1` → **`DW-FU-1-1`** (story `1-1-package-spine-verdict-lattice-findings-registry…`) — bmad-loop emits a bare
  `DW-<n>` per run, which collides with the next damped story; renamed on promotion.

---

# Deferred Work

> **Re-reconciled 2026-07-29 against conda-forge-expert v8.81.0** (Round-4 code-audit
> remediation). Each entry re-checked against the live tree; **1 of 5 is resolved, 4 stand**:
>
> - **`pixi build --manifest-path` (entry 1) — RESOLVED, and not by this pass.** The root
>   `pixi.toml` tasks already target the member package by `cwd` rather than the missing
>   flag (`pyforge-{mason,steward}-build-conda`, with the reason in an inline comment), so
>   the tasks the entry describes as failing do not fail. Re-verified against the newly
>   floored pixi **0.74.0**: `pixi build --help` still exposes only `--path`, no
>   `--manifest-path`, so the `cwd` workaround remains the correct shape rather than
>   something to revert. The entry described already-fixed code.
> - **Inline `.gitignore` comments (entry 2) — STILL OPEN, confirmed live.**
>   `pyforge-doctor/.gitignore` and `pyforge-warden/.gitignore` both still read
>   `/dist/          # pypi: wheel + sdist (...)`; gitignore has no trailing-comment
>   syntax, so both patterns remain dead and those directories are not ignored.
> - **Missing package LICENSE files (entry 3) — STILL OPEN.** `ls src/shared/packages/*/LICENSE*`
>   returns nothing while every sibling `pyproject.toml` declares MIT.
> - **DW-1 / DW-FU-1-1 follow-up review — STILL OPEN.** Unchanged.
>
> Nothing was re-severitied and nothing was closed in place: the one resolved entry is
> recorded as resolved-by-prior-work, not claimed by this pass.

> **Promotion pass 2026-07-30** — the Epic-1 continuation run (stories 1.2 / 1.3 / 1.10,
> bmad-loop run 20260730-001132-58f6) left 12 entries in the gitignored Tier-3 file that
> `deferred-work-check` flagged as `tier3-only-deferral`. Promoted here verbatim: bodies are
> unedited and nothing was re-severitied, per this ledger's standing copy-not-curation rule.
> The one change is the id — bare `DW-2` became `DW-FU-1-3`, because bmad-loop emits a generic
> per-run id that the next damped story would collide with.
>
> **Two entries were RESOLVED by the work in the same commit range, and are recorded as
> resolved rather than edited in place:**
>
> - *"No project-policy source anywhere in the repo currently supplies `gate_mode="none"` or
>   `max_followup_reviews=2`"* (Story 1.10 review) — **RESOLVED.** Nine tracked
>   `planning-artifacts/marshal-policy.toml` station layers now supply `gate_mode = "none"` and
>   per-station `verify_commands`, and `marshal config --write-harness-policy` plus convention
>   lookup give them a caller. Verified live: all nine render `gate=none`, `fu=2`.
> - *"restoring `max_followup_reviews = 2` via pyforge-marshal's project-policy layer alone
>   under-scopes the fix … the only homes for a repo-wide seed value are Marshal's
>   `DEFAULT_POLICY` or the global custom layer"* (Story 1.10 follow-up review) — **RESOLVED,
>   and it corrected this session's first attempt.** The nine layers each restated
>   `max_followup_reviews = 2`; that is nine copies of one repo-wide decision, exactly what the
>   finding warned against. The key was moved to `DEFAULT_POLICY` and dropped from every layer.
>   Composition provenance now reports `max_followup_reviews: 2 (layer=default)`, and a new
>   station inherits it instead of having to remember it.

## DW-1-1-1 — The `pyforge-mason`, `pyforge-steward`, and `pyforge-warden` `*-build-conda` pixi tasks (root `p…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: The `pyforge-mason`, `pyforge-steward`, and `pyforge-warden` `*-build-conda` pixi tasks (root `pixi.toml`) invoke `pixi build --manifest-path ...`, a flag the installed pixi (0.73.0) does not have (`pixi build --help` only exposes `--path`), so all three tasks fail when run.
  evidence: Confirmed live against the installed `pixi build --help` output while implementing Story 1.1's own `pyforge-marshal-build-conda` task, which mirrors the same block but was written with `--path` instead to avoid propagating the bug. Pre-existing in already-merged code; outside this story's declared surface (`src/shared/packages/pyforge-marshal/**` + root `pixi.toml` additions only).

  status: done 2026-07-30

  verified: 2026-07-30 — ALREADY RESOLVED, confirming the 2026-07-29 header note by measurement: `--manifest-path` appears exactly 3 times in the root `pixi.toml` and ALL THREE are inside comments (`:142`, `:171`, `:206`) — zero occurrences in any `cmd =`. mason (`:141-142`) and steward (`:170-171`) target the member by `cwd`; marshal (`:210`) uses `--path`. SIDE FINDING, worth its own cleanup: the surviving comments are now factually wrong. `:206-209` still asserts 'the pyforge-steward block this mirrors uses `--manifest-path` … steward's own build-conda task fails identically' — steward was fixed at `:170-171`, so that NOTE now libels working code. `:142`/`:171` also still cite pixi '0.73.0' against a repo floor of 0.75.0.

## DW-1-1-2 — `pyforge-doctor` and `pyforge-warden`'s package `.gitignore` files put comments inline after the…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: `pyforge-doctor` and `pyforge-warden`'s package `.gitignore` files put comments inline after the `/dist/` and `/dist-conda/` patterns; gitignore has no trailing-comment syntax, so both patterns are dead and those directories are not ignored (steward/mason use bare lines and are fine; marshal's copy of the same defect was fixed in this story's review pass).
  evidence: Reproduced live during the Story 1.1 review — probe files created under `pyforge-marshal/dist/` appeared as untracked until the comments were moved to their own lines; doctor's and warden's `.gitignore` are byte-identical to the pre-fix marshal file. Pre-existing in already-merged sibling packages, outside this story's surface.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN and WIDER than recorded — the entry named doctor and warden; it is now FOUR packages. `pyforge-warden/.gitignore:2-3`, `pyforge-doctor/.gitignore:2-3`, `pyforge-scribe/.gitignore:2-3` and `pyforge-herald/.gitignore:2-3` all carry the trailing-comment form `/dist/          # pypi: wheel + sdist (python -m build)`. gitignore has no trailing-comment syntax, so all eight patterns are dead. marshal (`:6-7`) and atlas (`:6`) use bare lines and are clean — the defect spread to scribe and herald by the same clone-the-sibling route that created it.

## DW-1-1-3 — Every pyforge sibling package (doctor, warden, steward, mason, and now marshal) declares `licens…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: Every pyforge sibling package (doctor, warden, steward, mason, and now marshal) declares `license = { text = "MIT" }` in `pyproject.toml` but ships no LICENSE file in the package directory, so built wheels/sdists/conda artifacts carry no license text.
  evidence: `ls src/shared/packages/*/LICENSE*` returns nothing while every sibling `pyproject.toml` declares MIT. Repo-wide sibling convention predating this story; fixing marshal alone would diverge from the mirror-the-siblings mandate, so it needs a one-sweep fix across all five packages.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and the sweep is now bigger: `ls src/shared/packages/*/LICENSE*` still returns nothing, across all EIGHT sibling packages (atlas, doctor, herald, marshal, mason, scribe, steward, warden) — the entry counted five. Every sibling `pyproject.toml` still declares `license = { text = "MIT" }` with no LICENSE file to ship.

## DW-1-1-4 — The `pyforge-mason-build-dist` and `pyforge-steward-build-dist` pixi tasks (root `pixi.toml`) ru…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: The `pyforge-mason-build-dist` and `pyforge-steward-build-dist` pixi tasks (root `pixi.toml`) run `python -m build` without `--no-isolation`, so `python -m build` creates an isolated venv and pip-fetches `hatchling` from PyPI — the `hatchling` deliberately provisioned in each feature block is dead weight, and the tasks hard-fail in the air-gapped/offline environments this repo explicitly supports (warden and doctor's equivalent tasks pass `--no-isolation`; marshal's copy of the same defect was fixed in this story's third review pass).
  evidence: Root `pixi.toml` shows warden/doctor build-dist cmds with `--no-isolation` and steward/mason without it; marshal's task mirrored steward/mason and was confirmed fixed live in this pass (wheel + sdist built successfully against the in-env hatchling with `--no-isolation` added). Pre-existing in already-merged sibling blocks, outside this story's surface.

  status: done 2026-07-30

  verified: 2026-07-30 — ALREADY RESOLVED. Every `*-build-dist` task in the root `pixi.toml` now passes `--no-isolation` — filtering the build-dist commands for ones lacking the flag returns nothing. mason (`:146`) and steward (`:175`), the two the entry named, both read `python -m build --no-isolation --outdir dist`. The air-gapped failure mode is closed.
### DW-FU-1-1: Follow-up review still recommended for 1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 1) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260725-234618-4c9d; this entry preserves the lingering recommendation for a deliberate later review.
status: open

verified: 2026-07-30 — CONFIRMED STILL OPEN — the recommended independent follow-up never happened. Grepping the whole of `planning-artifacts/` (32 files) for `1-1-package-spine` matches only `sprint-status-ledger.yaml` and this ledger; no review artifact exists for the story.

## DW-1-2-1 — `architecture.md`'s AD-23 rule text still says the story key is "purely numeric on both parts", contradicting AD-38

<!-- id assigned 2026-07-30 during the verification campaign: this entry was promoted
     with no heading and no status, so neither `normalize_deferred_ledgers.py` nor any
     id-based count could see it. Nothing cited it (it had no id), so assigning one
     breaks no references. -->

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-2-story-identity-merge-subject-rendering-and-feed-completeness.md`
  summary: `architecture-pyforge-marshal-2026-07-25/architecture.md`'s AD-23 rule text still literally says the canonical story key is "purely numeric on both parts," directly contradicting AD-38 (added the same day), which requires an optional ordered suffix to be preserved on read.
  evidence: Confirmed live by reading the architecture file during Story 1.2's implementation: AD-23's rule sentence is unamended even though the 2026-07-25 adversarial review (`architecture-pyforge-marshal-2026-07-25/reviews/review-ad25-39-adversarial-2026-07-25.md`, finding F-12) already flagged this exact contradiction as HIGH and noted the harness's own `bmad-loop run --story` documents accepting a split suffix (`2-6a`). Story 1.2's `core/identity.py` implements the epics.md-and-AD-38-correct behavior (suffix preserved, lowercased) per its own Design Notes, but the architecture document itself was left self-contradictory for the next reader who trusts AD-23's rule text without also reading identity.py's docstring. Pre-existing in already-final planning artifacts, outside this story's declared surface (`core/identity.py`, `core/findings.py`, `core/verdict.py`, their tests).

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and the contradiction is now visible inside a
  single document rather than across two. `architecture.md:221` still reads "the canonical story
  key is `<epic>.<seq>`, purely numeric on both parts", while the same file's summary table at
  `:382` reads "story key `<epic>.<seq>` with an optional ordered suffix, normalized on read
  (AD-23, AD-38)" — citing AD-23 as authority for the very rule AD-23's own text denies. AD-38
  is present at `:361`. Unamended since 2026-07-25.

## DW-1-3-1 — `core/policy.py`'s `content_hash` (and therefore `materialize()`'s content-addressed filename) i…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-3-layered-policy-composition-with-provenance-and-validation.md`
  summary: `core/policy.py`'s `content_hash` (and therefore `materialize()`'s content-addressed filename) is computed over each policy field's raw, UNREDACTED value — so once a real policy key ever becomes secret-shaped (none of the 9 shipped in Story 1.3 are), the materialized artifact's filename would be a deterministic fingerprint of that secret, even though the file's own body correctly redacts it via `policy.redact()`.
  evidence: Found during Story 1.3's adversarial + edge-case review passes (both reviewers independently flagged it). Reproduced by inspection: `EffectivePolicy.content_hash` and `cli/config.py::_policy_fields_payload()` both read `field.value` directly; only the payload path calls `redact()` before serializing for the file BODY, while the hash used for the FILENAME does not. Currently inert (no real secret-shaped key exists — the spec's own Never bullet says "do not invent a real secret key today"), but the tension is real: hashing the redacted value instead would make two different secrets that redact identically collide (defeating write-once correctness), so the fix is a genuine threat-model decision, not a mechanical patch. Needs a human call before any future story introduces a real secret-shaped policy key.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — and the behaviour is now deliberately documented, which does not close the concern. `core/policy.py:569-582`'s own `content_hash` docstring states it hashes 'over the RAW (unredacted) values … (redaction is a display/persistence concern, not an identity one)', while `cli/config.py:211` and `:213` still apply `policy.redact()` to the file BODY only. Note the docstring's stated rationale answers a DIFFERENT question than this entry asks — it justifies not hashing redacted values (collision avoidance), and says nothing about the filename becoming a fingerprint of a secret. Still inert: no secret-shaped key exists among the 9 shipped.

## DW-1-3-2 — `schemas/policy.json`'s `policyField` `$defs` entry does not constrain the TYPE of `value`/`raw_…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-3-layered-policy-composition-with-provenance-and-validation.md`
  summary: `schemas/policy.json`'s `policyField` `$defs` entry does not constrain the TYPE of `value`/`raw_source` (only the key set and the `layer` enum are checked), so a materialized document with a wrong-typed value (e.g. a string where `max_dev_attempts` expects an int) still validates against the schema.
  evidence: Found during Story 1.3's adversarial review pass. Confirmed by reading `schemas/policy.json`: the reused `policyField` shape gives `value`/`raw_source` a `description` but no `type` constraint, because the same `$defs` entry is shared across all 9 policy keys whose value types differ (str/int/tuple-as-array/dict). A precise fix needs per-field-name conditional typing (mirroring `pyforge-doctor/src/pyforge/doctor/data/report-schema.json`'s `if/then/else` pattern) — real schema-authoring effort, not a one-line change. Outside this story's `Effort: M` budget.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, verified by loading the schema rather than reading it. Parsing `schemas/policy.json` and inspecting `$defs.policyField.properties` gives exactly: `value: ['description']`, `layer: ['enum', 'description']`, `raw_source: ['description']` — so `value` and `raw_source` still carry NO `type` keyword and a wrong-typed materialized document still validates. No `if/then/else` per-field conditional typing was added.

## DW-1-3-3 — `cli/config.py::materialize()` can leave an orphaned `.policy-*.tmp` file in the target director…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-3-layered-policy-composition-with-provenance-and-validation.md`
  summary: `cli/config.py::materialize()` can leave an orphaned `.policy-*.tmp` file in the target directory if the process is killed unhandleably (e.g. `SIGKILL`, host crash) between `tempfile.mkstemp()` and `os.replace()` — no sweep/cleanup mechanism exists anywhere in this package to reclaim it later.
  evidence: Found during Story 1.3's edge-case review pass. Confirmed by reading `materialize()`: its `except BaseException: tmp_path.unlink(...); raise` cleanup only runs for exceptions the interpreter gets to handle, which a `SIGKILL` or crash bypasses entirely. Low-probability (requires an unhandleable interrupt at a narrow window) and no loop-home/cleanup story exists yet to own a general tmp-file sweep (Story 1.4+/`[cleanup]` policy territory) — outside this story's surface.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — no sweep mechanism exists. `cli/config.py:317` still names the temp file `.pid{os.getpid()}.t{threading.get_native_id()}.tmp`, and grepping the whole `pyforge/marshal/` package for a sweep/orphan/tmp-glob reclaimer returns only the unrelated `[sweep]` stanza in the harness template. A SIGKILL between `mkstemp` and `os.replace` still strands the file permanently.
### DW-FU-1-3: Follow-up review still recommended for 1-3-layered-policy-composition-with-provenance-and-validation after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-1-3-layered-policy-composition-with-provenance-and-validation.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260730-001132-58f6; this entry preserves the lingering recommendation for a deliberate later review.
status: open

verified: 2026-07-30 — CONFIRMED STILL OPEN — same measurement as its 1-1 twin. `1-3-layered-policy` matches only `sprint-status-ledger.yaml` and this ledger across all of `planning-artifacts/`; no review artifact was ever produced.

## DW-1-10-7 — No project-policy source supplies `gate_mode="none"` / `max_followup_reviews=2`, so the first real `write_policy_toml` caller would silently regress both

<!-- id assigned 2026-07-30 during the verification campaign: promoted with no heading and
     no status, so it was invisible to every id-based count. Nothing cited it. -->

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: No project-policy source anywhere in the repo currently supplies `gate_mode="none"` or `max_followup_reviews=2` for `pyforge-marshal`, so the first real invocation of `write_policy_toml` (once a later story wires it up) will render `gates.mode="per-story-spec-approval"` and `limits.max_followup_reviews=1` — Marshal's own `DEFAULT_POLICY` values — silently reintroducing the exact gate-pause and follow-up-review-damping regressions the live hand-edited `.bmad-loop/policy.toml` currently guards against (the latter already caused a documented incident, DW-AD23-3, across atlas/marshal/warden).
  evidence: Found during Story 1.10's adversarial review. Confirmed by grepping every `.bmad-config.toml`/`.bmad-config.user.toml` under `_bmad-output/projects/pyforge-marshal/` for `gate_mode`/`max_followup_reviews` — no match anywhere. `core/policy.py`'s `DEFAULT_POLICY` pins `gate_mode="per-story-spec-approval"` and `max_followup_reviews=1`, both weaker than the live tracked file's `mode="none"`/`max_followup_reviews=2`. Not this story's problem (Story 1.10 only renders a given `EffectivePolicy`; establishing pyforge-marshal's own project-policy layer is Story 1.4/1.7's concern), but whichever story first wires a real caller to `write_policy_toml` must supply that project layer or this regression ships silently.

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED, and by both halves independently, confirming the header's
  claim by measurement. `gate_mode`: NINE tracked `planning-artifacts/marshal-policy.toml`
  station layers now declare `gate_mode = "none"` (9 files matched, all 9 identical).
  `max_followup_reviews`: seeded once in `core/policy.py:150` as `"max_followup_reviews": 2`,
  with ten lines of inline reasoning at `:141-150` naming the repo-wide framing and the five
  damped stories. The real caller the entry anticipated also exists now
  (`cli/config.py:128` `--write-harness-policy`), so the regression window it describes is
  closed rather than merely unreached.

## DW-1-10-1 — `adapters/harness_bmadloop.py`'s vendored `_POLICY_TEMPLATE` is a hand-copied snapshot of `bmad_…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: `adapters/harness_bmadloop.py`'s vendored `_POLICY_TEMPLATE` is a hand-copied snapshot of `bmad_loop` 0.9.0's schema with no drift detector; root `pixi.toml` pins `bmad-loop = ">=0.9.0"` with no upper bound, so a routine re-solve installing a newer harness version with a renamed/added/changed-default key would silently go unnoticed by every existing test.
  evidence: Found during Story 1.10's adversarial review. Confirmed by reading `pixi.toml`'s `bmad-loop = ">=0.9.0"` pin (no ceiling) and `_POLICY_TEMPLATE`'s own docstring, which states the template was "verified once ... rather than imported at runtime." This repo already has an equivalent-purpose mechanism for a structurally similar problem (`scripts/bmad_drift_check.py`, `llms-full-check`) but nothing analogous protects this new vendored artifact. Deliberately out of this story's `Effort: M` scope (the spec explicitly chose vendoring over an `import bmad_loop` dependency to avoid a root pixi.lock re-solve); a lightweight version-pinned drift check is a reasonable follow-up for whichever story next touches this file.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN on both halves. The pin still has no ceiling: `pixi.toml:926` reads `bmad-loop = ">=0.9.0"`. And no drift detector guards the vendored snapshot — grepping `scripts/*.py` and the package's own `tests/` for `_POLICY_TEMPLATE` returns nothing, so the template at `adapters/harness_bmadloop.py:81` is still unprotected against a renamed or re-defaulted harness key.

## DW-1-10-2 — `write_policy_toml`'s unconditional whole-file overwrite will silently discard harness-native st…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: `write_policy_toml`'s unconditional whole-file overwrite will silently discard harness-native state that legitimately lives in the same file outside Marshal's control — `bmad-loop mux set <name>` persists `[mux].backend`, and the TUI persists resized pane geometry (`[tui].left_width`/`.runs_height`/`.deferred_height`/`.tasks_height`) — the moment this rendering path runs against a live loop home more than once.
  evidence: Found during Story 1.10's adversarial review. Confirmed in the installed `bmad_loop` 0.9.0 source: `policy.py::write_mux_backend()` rewrites `[mux].backend` in place, and `TuiPolicy`'s pane-dimension fields are documented as written by the TUI on resize. This is a direct consequence of AD-12/AD-35's own "written whole -- never patched, never merged" invariant (epics.md's Story 1.10 AC text, not a choice this story's spec introduced) — resolving it would need an architecture-level carve-out (e.g. round-tripping `[mux]`/`[tui]` from the pre-existing file before overwriting everything else), which is a product decision, not a mechanical patch.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — now stated outright in the code. `write_policy_toml`'s docstring (`adapters/harness_bmadloop.py:281-282`) says: 'Never reads an existing file at that path first: every call fully replaces any prior content, including hand-edited or unrelated bytes.' The harness-owned sections are in the vendored template (`[tui]` at `:184`, `[mux]` at `:187`), so a second render does not merely drop live pane geometry and the `mux set` backend — it resets them to template values.

## DW-1-10-3 — This story's untrack (`git rm --cached .bmad-loop/policy.toml`) only closes the F-1 cross-projec…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: This story's untrack (`git rm --cached .bmad-loop/policy.toml`) only closes the F-1 cross-project bleed going forward from this merge; any loop-home branch that diverged BEFORE this fix landed (the motivating example, `loop-pyforge-herald`, held 17+/27− of herald-specific policy on the shared tracked file at review time) still carries those tracked commits and needs a manual rebase/re-merge to actually stop bleeding.
  evidence: Found during Story 1.10's adversarial review. `loop-pyforge-herald`'s divergent state is already documented in this project's own memory (`project_open_items_2026-07-26.md`'s "Marshal (station owner)" section) as of the review date; nothing in this story's diff or ACs names a remediation step for already-diverged branches. Operational/rollout concern (a manual git operation per affected home), not a code defect this story's surface can fix.

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED — the divergence this entry worried about is gone. Checked ALL NINE `loop/pyforge-*` branches (atlas, doctor, genesis, herald, marshal, mason, scribe, steward, warden): `git show <branch>:.bmad-loop/policy.toml` fails on every one, so no branch still carries a tracked copy — including `loop/pyforge-herald`, the motivating example that held 17+/27− of herald-specific policy at review time. The untrack propagated to every home; no manual rebase is outstanding.

## DW-1-10-4 — Between this story's merge (which untracks `.bmad-loop/policy.toml`) and the later story that wi…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: Between this story's merge (which untracks `.bmad-loop/policy.toml`) and the later story that wires a real caller to `write_policy_toml`, any FRESH loop home/clone — and any existing home whose unmodified tracked copy git deletes on pull — has no `.bmad-loop/policy.toml` at all, so bmad-loop runs on its stock defaults: `scm.isolation="none"` (dev sessions edit the live checkout in place), `verify.commands=[]` (no deterministic verify gate), `review.trigger="recommended"`, `session_timeout_min=90`; rollout needs a per-home restore/render step until the renderer is wired.
  evidence: Found during Story 1.10's follow-up review (second pass). The diff deletes the tracked file while the module docstring itself states "no CLI wires this module's functions yet"; bmad_loop 0.9.0's stock defaults were confirmed against its installed `policy.py` dataclasses. Distinct from the two existing entries (the first-caller DEFAULT_POLICY regression, and pre-diverged branches needing rebase): this is the no-file-at-all window, a direct consequence of the epic's own mandated sequencing (untrack last, wiring in Story 1.4/1.7), so it is an operational rollout concern outside this story's authority, not a code defect.

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED — both ends of the window are closed. A real caller now exists: `cli/config.py:128` declares `--write-harness-policy`, wired at `:447` and dispatching to the renderer at `:455`. And no home is currently bare: all nine `~/.bmad-loops/pyforge-*` homes have a live `.bmad-loop/policy.toml` present. The stock-defaults exposure the entry describes (`scm.isolation="none"`, `verify.commands=[]`) is therefore not live anywhere today.

## DW-1-10-5 — The `max_followup_reviews = 2` value in the (now untracked) live policy.toml was explicitly bran…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: The `max_followup_reviews = 2` value in the (now untracked) live policy.toml was explicitly branded a REPO-WIDE policy decision ("a repo-wide policy decision that has nothing to do with marshal", restored 2026-07-30 after five stories across three projects were damped by the default of 1), so restoring it via pyforge-marshal's project-policy layer alone (the existing ledger entry's Story 1.4/1.7 remedy) under-scopes the fix — in the new rendering model the only homes for a repo-wide seed value are Marshal's `DEFAULT_POLICY` (core/policy.py) or the global custom policy layer, and a template hardcode cannot work because `render_policy_toml` unconditionally overwrites `[limits].max_followup_reviews` from the composed `EffectivePolicy`.
  evidence: Found during Story 1.10's follow-up review (second pass). The deleted file's own 2026-07-30 comment (this diff, `.bmad-loop/policy.toml` lines 49-68) documents the repo-wide framing and the five damped stories (atlas 10.5/10.6, marshal 1.1, warden 6.3/5.1, yielding DW-AD23-3); `core/policy.py::DEFAULT_POLICY` pins 1. This is a resolution-shaping constraint for whichever story supplies the policy source — recorded as a NEW entry (the orchestrator owns the existing marshal-values entry; this does not modify or re-open it).

  status: done 2026-07-30

  verified: 2026-07-30 — RESOLVED exactly as the entry prescribed — the value was seeded in Marshal's `DEFAULT_POLICY`, not in a project layer. `core/policy.py:150` now declares `"max_followup_reviews": 2`, and `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` restates it ZERO times — confirming the nine-copies shape the review warned against was avoided. The entry named exactly two acceptable homes (DEFAULT_POLICY or the global custom layer); the first was used.

## DW-1-10-6 — The tracked `.bmad-loop/policy.toml` this story deletes carried curated operational commentary w…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`
  summary: The tracked `.bmad-loop/policy.toml` this story deletes carried curated operational commentary with no other tracked home — the A4/A6 authoring conventions from the pyforge-atlas retro, the hard-story model-escalation batch procedure, the atlas-gates restore instructions, the `--frozen` verify rationale, and the full max_followup_reviews=2 argument — which now survives only in git history (`git show 99ba90ea4e:.bmad-loop/policy.toml`) and in untracked per-home working copies; the still-relevant parts should be relocated to a tracked home (template comments, the future project-policy source, or project docs) when Story 1.4/1.7 establishes where policy values live.
  evidence: Found during Story 1.10's follow-up review (second pass). Directly visible in this story's diff (250 deleted lines, of which ~120 are curated commentary, not config); the A4/A6 block explicitly says "recorded here because this is where a loop operator looks." Not permanent loss (git history retains the blob), but a real discoverability regression; placement of each fragment depends on the policy-source design owned by later stories, so it is not mechanically patchable inside this story's declared surface (adapter + tests + .gitignore).
  status: open

  verified: 2026-07-30 — PARTIALLY RESOLVED, so held open for the remainder. Two fragments now DO have tracked homes: the `max_followup_reviews = 2` argument was relocated in full to `core/policy.py:141-150` (ten comment lines naming the repo-wide framing, the five damped stories and DW-AD23-3), and the A4/A6 authoring conventions live in the tracked `pyforge-atlas/planning-artifacts/retros/SYNTHESIS.md`. Not verified as relocated: the hard-story model-escalation batch procedure, the atlas-gates restore instructions, and the `--frozen` verify rationale. Those still survive only in `git show 99ba90ea4e:.bmad-loop/policy.toml` and untracked per-home copies.

> **Promotion pass 2026-07-31 (Stories 1.7-1.9 audit)** — nine entries from the
> gitignored Tier-3 ledger had no ids and therefore escaped `deferred-work-check`'s
> id-set comparison. They are copied below without editing their `source_spec`,
> `summary`, or `evidence` bodies. Stable story-scoped ids and current status/verification
> fields are the only additions. One entry was resolved by Story 1.9; eight remain open.

## DW-1-7-1 — The supported harness range had three unsynchronized declarations

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-7-preflight-adapter-config-seeding-and-first-run-acknowledgement.md`
  summary: The declared supported harness range (`>=0.9.0,<0.10`) is now hardcoded independently in THREE places — `pyproject.toml`'s `dependencies` entry, `pixi.toml`'s `bmad-loop` line, and `cli/init.py`'s own `_HARNESS_MIN_VERSION`/`_HARNESS_MAX_MINOR_EXCLUSIVE`/`_HARNESS_VERSION_RANGE_TEXT` constants that `run_preflight` validates the LIVE `bmad-loop --version` output against — with nothing keeping the third copy in sync with the first two.
  evidence: Found during Story 1.7's adversarial review pass. Confirmed by grep: all three literals exist independently, and unlike the pyproject.toml/pixi.toml pair (which `tests/meta/test_manifest_sync.py` already cross-checks), no test compares `cli/init.py`'s parsed tuple bounds against either manifest string. A future pin bump (e.g. Story 1.9's planned range change, or a routine `bmad-loop` upgrade) can update the two manifests and silently leave `_harness_version_in_range` validating against a stale range, so `marshal preflight` would wrongly pass (or wrongly block) once the two drift. Low severity today (all three still agree, and this repo's own installed `bmad-loop` is pinned at exactly 0.9.0), but real: fixing it needs either deriving the tuple bounds from `_HARNESS_VERSION_RANGE_TEXT` at import time (cuts three sources to two) or a `test_manifest_sync.py`-style meta-test extended to also parse `cli/init.py`'s constants — a deliberate design choice about where the ONE source of truth should live, not a one-line patch.

  status: done 2026-07-31

  verified: Story 1.9 moved the range constants into `adapters/harness_bmadloop.py`, the FR-52 seam that declares the supported range, and added `tests/meta/test_manifest_sync.py::test_harness_range_constants_match_pyproject_dependency_pin`; the existing manifest cross-check covers `pixi.toml` transitively.

## DW-1-8-1 — Preflight lacks init and teardown's Git-ref-shape slug guard

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `run_preflight` (Story 1.7) does not apply the same git-ref-shape guard (`.`/`..`/`.lock` component rejection) that `run_init` and now `run_teardown` both apply on top of `core.policy._is_valid_project_slug` — a slug shape git itself would refuse as a branch-name component reaches real I/O in `run_preflight` and surfaces as an opaque `MRS-PREFLIGHT-004`-class error instead of a crisp pre-I/O rejection.
  evidence: Found during Story 1.8's adversarial review pass, while verifying an inline comment in the new `run_teardown` code that (incorrectly, now corrected) claimed `run_preflight` already shared this guard. Confirmed by code inspection: `run_preflight`'s slug gate (`cli/init.py`, its `MRS-PREFLIGHT-010` check) calls only `policy._is_valid_project_slug(slug)`, with no `.`/`..`/`.lock` check anywhere in that function. Pre-existing gap, not introduced by this story; fixing it is a one-line addition to `run_preflight` but is Story 1.7's surface, not this story's.

  status: open

  verified: 2026-07-31 — CONFIRMED STILL OPEN. `run_preflight` calls only `policy._is_valid_project_slug(slug)`; `run_teardown` still carries an inline comment explicitly recording the missing companion guard.

## DW-1-8-2 — Teardown hardcodes the integration branch as `main`

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `run_teardown` always calls `is_branch_merged(repo_root, branch, into="main")` with no way to point teardown at a repo whose default integration branch is not literally `main` (`master`, `trunk`, etc.) — such a repo would hard-fail every teardown invocation with an opaque `MRS-TEARDOWN-002` from git failing to resolve `refs/heads/main`.
  evidence: Found during Story 1.8's adversarial review pass. This mirrors an already-adjudicated hardcoding: Story 1.4's `add_worktree` calls already hardcode `base="main"` when minting a loop-home branch, and `EffectivePolicy` (Story 1.3) deliberately owns only 9 fixed keys, none naming a base/integration branch. `is_branch_merged`'s new `into` parameter makes the assumption more visible than before, but does not introduce it. Needs a product decision (add a tenth policy key, or accept `main`-only as a permanent constraint of this factory) before it can be fixed — out of scope for an Effort:S story.

  status: open

## DW-1-8-3 — Teardown has a branch-deletion TOCTOU window

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `run_teardown` always calls `delete_branch(repo_root, branch, force=True)` once removal is authorized (both on the clean/merged path and the forced-refusal path) — if new commits land on the branch ref between `is_branch_merged`'s read and this call (a concurrent process writing to the same worktree via some path other than the worktree teardown just removed), they are force-deleted with `-D` and never re-verified, without the operator's own `--force` ever having been the reason.
  evidence: Found during Story 1.8's adversarial review pass. The window is narrow (the worktree itself is removed before `delete_branch` runs, and git worktrees are exclusive to one branch, so only an out-of-band `git update-ref`/push from a separate process could land new commits in it) and no architecture doc in this repo describes protecting against concurrent multi-process mutation of the same loop-home branch — AD-11's isolation model assumes one operator, one loop home. Real but requires a broader concurrency-control design (e.g. re-verifying `is_branch_merged` immediately before `delete_branch`, or locking) that is out of scope for an Effort:S story.

  status: open

## DW-1-8-4 — Teardown cannot see valuable gitignored content

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `marshal teardown`'s refusal model cannot see gitignored content -- `git status --porcelain` omits ignored files and a plain unforced `git worktree remove` deletes them, so a loop home whose most valuable content sits in gitignored paths (`.bmad-loop/runs/` state, drafted-but-unpromoted Tier-3 story specs, logs) reads as clean and is destroyed with exit 0.
  evidence: Found by Story 1.8's follow-up adversarial review, live-verified two ways -- unforced `git worktree remove` exits 0 and recursively deletes ignored files in a scratch repo, and the real `~/.bmad-loops/pyforge-marshal` home read `git status --porcelain`-clean at review time while hosting an active run with unpromoted work (the precise artifact class the pyforge-warden incident lost). Not patchable naively -- EVERY loop home carries gitignored content (`run_init`'s own marker/symlink, `.bmad-loop/runs/`), so refusing on any ignored content would refuse every ordinary teardown and train the gate away (the exact F-14 failure mode AD-29's amendment warns about). Distinguishing disposable from precious gitignored content is what AD-29's promotion-reachability predicate exists for; this entry is concrete evidence for Epic 4's wiring of `_unreachable_promotions` (a hardcoded no-op today by the spec's own Never-clause).

  status: open

## DW-1-8-5 — Teardown can destroy nested registered worktrees

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: Tearing down a loop home silently destroys nested REGISTERED run worktrees inside it (`<home>/.bmad-loop/runs/<run>/worktrees/<story>`, this repo's own bmad-loop layout) including any uncommitted story work, and leaves orphaned prunable registrations behind -- `run_teardown` interrogates only `loop/<slug>` and never consults the port's existing `list_worktrees` for worktrees nested under the removal target.
  evidence: Found by Story 1.8's follow-up adversarial review, live-verified -- unforced `git worktree remove <home>` on a home containing a nested registered worktree succeeds, recursively deletes it including uncommitted files, and leaves a prunable orphan block in `git worktree list --porcelain`; six of the eight fleet homes at `~/.bmad-loops/` contained such nested worktrees at review time. Committed nested work survives as `bmad-loop/...` branch refs in the common git dir; uncommitted work is lost. A naive any-nested-worktree refusal would fire on every fleet home (universal refusal, gate trained away), so the fix needs a designed policy -- per-nested-worktree dirty/merged checks and a post-removal `git worktree prune` -- a scope decision beyond this Effort:S story's contract, adjacent to Epic 4's AD-29 wiring.

  status: open

## DW-1-8-6 — Teardown has no active-run liveness guard

- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-teardown-that-refuses-to-destroy-work.md`
  summary: `marshal teardown` has no liveness guard -- nothing checks whether a bmad-loop run is actively executing in the home (tmux session, fresh run state, lock), so an operator teardown mid-run destroys the run's in-flight state without refusal, since an active run's entire footprint lives in gitignored `.bmad-loop/runs/` paths the dirty check cannot see.
  evidence: Found by Story 1.8's follow-up adversarial review. The 8-home fleet at `~/.bmad-loops/` runs unattended, and a live run's worktrees/logs/state are all inside gitignored paths (see the companion gitignored-blindness entry), so both refusal probes pass while a story is mid-implementation; the check-then-remove sequence is also unsynchronized with any concurrent writer (same class as the already-deferred delete-branch TOCTOU entry). No liveness mechanism exists anywhere in Marshal's architecture yet to consult -- introducing one (probe choice, staleness thresholds, lock protocol) is a design decision interacting with the same Epic 4 refusal-extension seam, not a patch.

  status: open

## DW-1-9-1 — Marshal's README still describes a Story 1.1 skeleton

- source_spec: `_bmad-output/implementation-artifacts/spec-1-9-packaging-distribution-and-version-reporting.md`
  summary: `src/shared/packages/pyforge-marshal/README.md`'s top "Status" blurb still says "build skeleton (Story 1.1) ... No real command exists yet -- `marshal --version` / `marshal --help` are the only working invocations," which has been false since Story 1.4 shipped `init`/`homes`/`preflight`/`teardown`.
  evidence: Found during Story 1.9's adversarial review pass. Confirmed by reading the README's opening paragraph against the shipped command set in `cli/main.py`'s own docstring (five real subcommands, not zero). Pre-existing across five prior stories, not introduced by this one; Story 1.9's own diff only appended a "Platforms" section and a new command line beneath the stale blurb without correcting it, since a full README rewrite was explicitly out of this Effort:M story's declared surface (`pyproject.toml`/`pixi.toml`, packaging/version-reporting behavior) -- fixing it is a documentation-only patch some future story (or a direct edit) should pick up.

  status: open

  verified: 2026-07-31 — CONFIRMED STILL OPEN. The README's opening Status block still says no real command exists, while `cli/main.py` documents and wires five subcommands.

## DW-1-9-2 — The future run journal must record Marshal and harness versions

- source_spec: `_bmad-output/implementation-artifacts/spec-1-9-packaging-distribution-and-version-reporting.md`
  summary: Epic 3's run-journal writer (`core/journal.py`, Stories 3.1/3.2) must record BOTH `marshal_version` and `harness_version` per run to complete FR-57's "both versions appear in the journal for every run" clause -- Story 1.9 deliberately implemented only the `--version`/preflight halves of FR-57 (its spec's own Never boundary: no journal write path two epics early).
  evidence: FR-57's journal clause is explicit in the PRD; `core/journal.py` does not exist yet (`supervisor/__init__.py` is a reserved stub), so the write cannot land now. Story 1.9's spec's Design Notes promised exactly this ledger entry ("log a deferred-work entry that Story 3.1's journal writer must record {marshal_version, harness_version} per run once it exists") but no such entry had ever been appended -- its absence was itself a Story 1.9 follow-up-review finding.

  status: open

## DW-AUD-2026-07-31-1 — Stories 1.7-1.9 shipped without canonical memlog reconciliation

- source: `scripts/spec_surface_check.py`, Story 1.7-1.9 implementation specs, and PR #175
  summary: The detector's 23 governed-file findings were the implementation surface of completed Marshal Stories 1.7-1.9, not 23 unexplained defects. PR #175 merged the reviewed and verified preflight/config-seeding, safe-teardown, and packaging/version-reporting work, but `spec-pyforge-marshal/.memlog.md` stopped at Story 1.6 and omitted the delivery decisions and residual risks.
  evidence: Merge `b70f7591f29` changed 25 Marshal files (+5160/-93), including the 23 governed source/test files reported by `spec-surface-check`. All three Tier-3 story specs have `status: done`, review-triage logs, verification records, and final revisions. The canonical memlog had no Story 1.7, 1.8, or 1.9 delivery event before this audit.
  action: Append substantive Story 1.7-1.9 delivery entries to the canonical memlog, including the nine promoted deferrals; do not treat a movement-only audit line or a rewritten detector baseline as reconciliation.
  status: done 2026-07-31

  verified: The staged memlog now records each story's shipped behavior, verification, and durable residual-risk disposition. `spec-surface-check` is rerun as part of this audit's verification.

## DW-AUD-2026-07-31-2 — Four Marshal-owned Dreams still have no Tier-2 Spec

- source: `scripts/dream_chain_check.py`
  summary: The repository-wide artifact audit ran `pixi run -e local-recipes dream-chain-check` and found four Dreams owned by Marshal without a corresponding Spec: `durable-runs`, `fidelity-enforcement`, `one-front-door`, and `pr-lifecycle`.
  evidence: The detector reported `INV-1 — 4 finding(s)` on 2026-07-31, with `owner=marshal`. Related discussion exists in Marshal and Genesis memlogs, but no complete four-Spec chain exists under `_bmad-output/projects/`.
  action: For each Dream, either run `bmad-spec` and place the resulting Spec under the owning project, or record an explicit retirement/absorption decision in the Dream and its owning project memlog so the chain checker has a durable disposition.
  status: open

## DW-AUD-2026-07-31-3 — Deferred-work detector ignores anonymous Tier-3 entries

- source: `scripts/deferred_work_check.py`
  summary: `deferred-work-check` compares only `DW-*` ids between Tier 3 and the tracked ledger, so nine real Story 1.7-1.9 deferrals with no ids produced a false-green result and remained vulnerable to teardown loss.
  evidence: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/deferred-work.md` contained nine consecutive id-less entries for Stories 1.7-1.9. Before this promotion, none appeared in the tracked ledger, yet `pixi run -e local-recipes deferred-work-check` passed. The detector's anonymous-entry validation applies to tracked ledgers, not Tier-3 inputs.
  action: Extend `deferred_work_check.py` to report anonymous Tier-3 entries (or compare normalized entry fingerprints in addition to ids), with a regression fixture proving an id-less Tier-3 deferral cannot pass merely because there is no id to compare.
  status: open

> **Promotion pass 2026-07-31 (Stories 1.4-1.6 audit)** — entries from the gitignored Tier-3 ledger that were missed previously.

## DW-1-4-1 — `cli/init.py`'s project-existence check (`MRS-INIT-002`) reads `_bmad-output/pro…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `cli/init.py`'s project-existence check (`MRS-INIT-002`) reads `_bmad-output/projects/<slug>/planning-artifacts` from whatever is checked out in the resolved repo root's LIVE working tree, not from the `main` ref specifically — while `add_worktree` bases the new branch on the literal `main` ref regardless. If the primary checkout is ever not actually on `main`, the two checks are validated against different git states (a project could be wrongly rejected, or a stale project could be wrongly accepted).
  evidence: Found during Story 1.4's adversarial review. Confirmed by code inspection: `fs.is_dir(planning_dir)` calls `Path.is_dir()` on the live filesystem, with no `git show main:...`/branch check anywhere in the path. Low real-world risk given this exact story's own AD-11 invariant (main is never checked out into a second worktree, so the primary checkout has no code path that moves it off main) — but that is an operating discipline, not an enforced guarantee, so a manual `git checkout <other-branch>` in the primary checkout during unrelated work would open the window. Needs a product decision (accept the AD-11-backed low-probability risk, or add a ref-based existence check) before treating it as a mechanical patch.

  status: open

## DW-1-4-2 — The `MRS-INIT-003` marker/symlink desync guard has two blind spots: (1) `_slug_f…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: The `MRS-INIT-003` marker/symlink desync guard has two blind spots: (1) `_slug_from_symlink_target` only recognizes the exact shape `projects/<slug>/planning-artifacts` — any other shape (a target written by a different tool, an absolute path) parses to `None`, so a real desync hiding behind an unrecognized shape evades the check; (2) the guard only compares the marker and symlink to EACH OTHER, never to the actually-requested slug, so a home whose marker and symlink consistently agree on a DIFFERENT project than the one just requested is treated as "not a desync" and gets silently reconciled onto the new slug with no warning that it was repurposed.
  evidence: Found during Story 1.4's adversarial review (two related findings merged). Confirmed by code inspection of `cli/init.py::_slug_from_symlink_target` and the `MRS-INIT-003` condition (`marker_slug is not None and link_slug is not None and marker_slug != link_slug`). Given each loop home's path is keyed by its own slug (`<root>/<slug>`), (2) can only arise from external tooling repointing a home's own marker/symlink to a different project — an anomalous, unlikely-but-real operator scenario. Needs a product decision on whether a third cross-check (against the directory's own slug) belongs to this story or to Story 1.6 (isolation verification, FR-4), which is explicitly the "prove homes are genuinely isolated" surface.

  status: open

## DW-1-4-3 — `adapters/fs_local.py`'s two atomic-write helpers disagree on stale-temp-file ha…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `adapters/fs_local.py`'s two atomic-write helpers disagree on stale-temp-file handling for the identical crash-orphan scenario: `write_text_atomic` opens its temp path with `O_EXCL` and hard-fails (`FsWriteError`) if a leftover temp file exists, while `repoint_symlink_atomic` silently `unlink()`s any pre-existing temp path first before proceeding.
  evidence: Found during Story 1.4's adversarial review. Confirmed by code inspection: both docstrings cite the same "pid+thread-id collision-safety" rationale, but implement opposite policies. Low-impact given the pid+thread-id-suffixed temp names already make a real collision extremely unlikely, but the inconsistency itself is a maintainability/correctness smell worth a follow-up cleanup pass to pick one policy.

  status: open

## DW-1-4-4 — `marshal init <slug>` has no protection against two concurrent invocations for t…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `marshal init <slug>` has no protection against two concurrent invocations for the same slug: there is an unguarded TOCTOU window both between `worktree_path_for_branch` (read) and `add_worktree` (write) in `cli/init.py::run_init`, and between `branch_exists` and the actual `git worktree add -b` inside `GitVcs.add_worktree`. Two concurrent runs can both observe "not yet provisioned," race, and one surfaces an opaque `MRS-INIT-004` rather than a clean "already in progress" outcome.
  evidence: Found during Story 1.4's adversarial + edge-case review passes (both reviewers independently flagged it). This repo's own documented history includes parallel-agent races over shared git/BMAD state (see `feedback_parallel_bmad_physical_paths.md`), so the scenario is realistic, not purely theoretical. A real fix (a lock file, or accepting git's own worktree-add race semantics as "good enough" with a clearer error) is a design decision spanning this story and possibly Story 1.6's isolation-verification surface — not a mechanical patch.

  status: open

  scope note (2026-07-31): this entry is the concrete, in-code instance of a wider question — nothing serializes concurrent writes to the SHARED Tier-2 artifacts (`epics.md`, this ledger, `sprint-status-ledger.yaml`) that every loop line writes. That question was raised against the Spec and PRD rather than this ledger, and was RESOLVED the same day by decomposition (PRD Q-10 / the Spec memlog decision): merge append-only inputs and re-derive regenerated outputs on main after landing; advisory append lock on the shared canonical Tier-3 store; the journal's two-writer case stays with F-6. Fixing this entry does not answer that question, and its resolution does not close this entry — the init TOCTOU remains its own open deferral.

## DW-1-4-5 — `cli/init.py::_loop_home_root()`'s real default fallback (`Path.home() / ".bmad-…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `cli/init.py::_loop_home_root()`'s real default fallback (`Path.home() / ".bmad-loops"`, used whenever `BMAD_LOOP_HOME_ROOT` is unset) has zero test coverage — every test in `tests/unit/test_init.py` and the integration test override the env var via an autouse/explicit fixture, so what an actual operator gets by default is never exercised.
  evidence: Found during Story 1.4's adversarial review. Confirmed by grep: `BMAD_LOOP_HOME_ROOT` is set in every test file that imports `run_init`/`main`. The code itself is a one-line `Path` join with low risk, but the coverage gap is real and mechanically closeable (a single test with `monkeypatch.delenv`) — recorded rather than patched now to keep this pass's diff scoped to the findings that change behavior, not just coverage.

  status: open

## DW-1-4-6 — `tests/unit/test_vcs_git.py` and `tests/integration/test_init_worktree.py` each …

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `tests/unit/test_vcs_git.py` and `tests/integration/test_init_worktree.py` each define an identical `_git(repo, *args)` subprocess-wrapping test helper instead of sharing one via `tests/conftest.py`, so a future fix to one copy can silently drift from the other.
  evidence: Found during Story 1.4's adversarial review. Confirmed by diff: both helpers are byte-identical (`subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)` plus the same returncode assertion). Minor test-hygiene issue with no runtime consequence.

  status: open

## DW-1-4-7 — `cli/init.py`'s printed `launch_line` (`cd <home> && export BMAD_ACTIVE_PROJECT=…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `cli/init.py`'s printed `launch_line` (`cd <home> && export BMAD_ACTIVE_PROJECT=<slug>`) is not shell-quoted; a `BMAD_LOOP_HOME_ROOT` override containing a space would produce a line that does not paste-and-run correctly (the slug itself cannot contain a space — `core.policy._is_valid_project_slug`'s charset already excludes it).
  evidence: Found during Story 1.4's edge-case review. Confirmed by code inspection of `run_init`'s `data["launch_line"] = f"cd {home} && export BMAD_ACTIVE_PROJECT={slug}"` — no `shlex.quote()` anywhere in the f-string. Low real-world likelihood (the loop-home root is normally under `~/.bmad-loops`, which has no spaces) but a real robustness gap for a deliberately overridable path.

  status: open

## DW-1-4-8 — `marshal init` has no guard against the total loop-home path length, despite thi…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `marshal init` has no guard against the total loop-home path length, despite this repo's own documented history of `pixi-build-python` panicking (byte-index underflow) on worktree paths beyond roughly 173 bytes — a sufficiently long project slug (up to the existing 255-char shape cap) plus a long `BMAD_LOOP_HOME_ROOT` override could still reproduce that failure class.
  evidence: Found during Story 1.4's edge-case review, corroborated by this project's own memory (`project_bmad_loop_worktree_path_length_limit.md`) and by `scripts/bmad-loop-worktree`'s own comment documenting the exact panic and the `~/.bmad-loops` short-root mitigation it already applies. Pre-existing risk, not newly introduced by this diff (the reference script has the identical gap) — the existing 255-char `_is_valid_project_slug` cap is a POSIX single-segment bound, not a total-path bound. Needs a product decision on whether Marshal should add a total-length check now or continue relying on the short default root as sufficient mitigation.

  status: open

## DW-1-4-9 — `cli/main.py::main` catches only `SystemExit` and `KeyboardInterrupt` — it has n…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `cli/main.py::main` catches only `SystemExit` and `KeyboardInterrupt` — it has no last-resort `except Exception` clamp, so any unanticipated exception escaping a subcommand handler still surfaces as a raw traceback with interpreter exit 1, outside Marshal's frozen `{0,1,2,3,4,130}` exit-code domain (AD-7).
  evidence: Found during Story 1.4's follow-up review (both reviewers flagged escape paths; the specific known escapes — `Path.cwd()` OSError, `Path.home()` RuntimeError, `UnicodeDecodeError` from marker reads and git output, pathlib `PermissionError` on the 3.12 floor — were all patched at their sources in that pass). The residual clamp is a pre-existing Story 1.1/1.3 design decision on the CLI spine (silently converting unknown bugs to `EXIT_USAGE` trades a loud traceback for domain purity), not a mechanical patch; it spans every current and future subcommand, so it deserves its own deliberate change rather than a review-pass side edit.

  status: open

## DW-1-4-10 — `tests/integration/test_init_worktree.py` — the only end-to-end proof of both wo…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-4-provision-a-loop-home.md`
  summary: `tests/integration/test_init_worktree.py` — the only end-to-end proof of both worktree acceptance criteria with the real `GitVcs`/`LocalFs` adapters — is executed by no automated gate: the default `pyforge-marshal-test` task excludes `@pytest.mark.slow`, the loop's verify command runs exactly that task, and no `.github/workflows/*` file invokes either marshal task, so `pyforge-marshal-test-slow` only runs when an operator remembers the spec's manual verification step.
  evidence: Found independently by both reviewers in Story 1.4's second follow-up review. Confirmed by grep: `pyforge-marshal-test-slow` appears only in `pixi.toml` and the spec; no CI workflow references either marshal task. Wiring it in is a decision about WHERE (a CI workflow vs. the loop's verify gate vs. a `depends-on` aggregate task) — the loop verify command is orchestrator-owned policy, so this needs a deliberate placement decision, not a review-pass side edit.

  status: open

## DW-1-5-11 — `cli/init.py`'s `tier3_backlink` step gives a real, non-empty DIRECTORY at the l…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-5-single-sourced-tier-3-store-via-backlink.md`
  summary: `cli/init.py`'s `tier3_backlink` step gives a real, non-empty DIRECTORY at the local Tier-3 path a dedicated `MRS-INIT-005` refusal, but a non-directory node (a stray plain FILE) at either the local path or the main checkout's canonical path falls through to the generic `MRS-INIT-004` via `repoint_symlink_atomic`'s/`ensure_dir`'s own internal clobber guards instead.
  evidence: Found independently by both reviewers in Story 1.5's review pass. Confirmed by code inspection: `fs.is_dir(local)` is False for a plain file, so the `remove_empty_dir`/`MRS-INIT-005` branch is never reached; `repoint_symlink_atomic`/`ensure_dir` still safely refuse (no data is destroyed), just under the less-specific code. Low real-world likelihood (why would a plain file occupy exactly this path?) and current behavior is already safe, so not patched now — a dedicated check would need a general `exists()`-style `FsPort` primitive this story's narrow surface doesn't otherwise need.

  status: open

## DW-1-5-13 — `tier3_backlink`'s convergence check compares the raw (unresolved) symlink target…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-5-single-sourced-tier-3-store-via-backlink.md`
  summary: `tier3_backlink`'s convergence check compares the raw (unresolved) symlink target string against `canonical` (`tier3_link_target == canonical`), whereas the ported reference `scripts/bmad-switch::ensure_tier3_backlink` uses `local.resolve() == canonical.resolve()`.
  evidence: Found during Story 1.5's adversarial review. Both `local`'s stored target and `canonical` are always computed identically via the same deterministic `repo_common_root()`/path-join logic on every invocation (Marshal never hand-configures this symlink, unlike the more varied historical states `bmad-switch` has to tolerate), so a divergence causing spurious non-convergence is unlikely in practice — but the inconsistency with the reference script's own comparison method is real and worth revisiting for full fidelity.

  status: open

  verified: 2026-07-31 — promoted in the second pass of this audit. Missed by the first pass, which swept the id-less Tier-3 block without reconciling its entry count against the tracked ledger — the same anonymous-entry blind spot recorded as `DW-AUD-2026-07-31-3`, reproduced by the audit that reported it.

## DW-1-5-14 — A failed `ensure_dir`/`repoint_symlink_atomic` after `remove_empty_dir` leaves the…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-5-single-sourced-tier-3-store-via-backlink.md`
  summary: If `fs.remove_empty_dir(local)` succeeds (clearing a stale empty local Tier-3 directory) but the immediately-following `fs.ensure_dir(canonical)` or `fs.repoint_symlink_atomic(local, canonical)` then fails, `local` is left with NOTHING (no directory, no symlink) — a worse state than before the removal — with no rollback.
  evidence: Found during Story 1.5's edge-case review. Confirmed by code inspection: no compensating write restores the removed directory in the `except FsError` branches after `remove_empty_dir`. Low practical impact since the removed directory was necessarily EMPTY (no data loss) and a subsequent successful re-run self-heals via the same "fresh backlink" path, but a true rollback would be more robust.

  status: open

  verified: 2026-07-31 — promoted in the second pass of this audit, alongside `DW-1-5-13`. Same miss, same cause.

## DW-1-5-12 — A home provisioned by `marshal init` alone still lacks the TOP-LEVEL `_bmad-outp…

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-5-single-sourced-tier-3-store-via-backlink.md`
  summary: A home provisioned by `marshal init` alone still lacks the TOP-LEVEL `_bmad-output/implementation-artifacts` symlink, yet `_bmad/bmm/config.yaml` hard-codes `implementation_artifacts: "{project-root}/_bmad-output/implementation-artifacts"` — so every config-resolving BMAD consumer inside such a home sees a dangling path and would materialize a real top-level directory on first write, forking Tier-3 state one level above the nested backlink this story creates, and `bmad-switch --current`'s desync warning fires on every marshal-provisioned home.
  evidence: Found during Story 1.5's follow-up adversarial review. Confirmed by inspection of `_bmad/bmm/config.yaml:8` (top-level path hard-coded), `scripts/bmad-switch::_ARTIFACT_LINKS`/`desync_warning` (requires BOTH top-level links to agree with the marker), and the epics: no later story creates the link — Story 1.6 only VERIFIES Tier-3 realpaths, Story 1.7 seeds adapter configs. The spec deliberately scoped the top-level compatibility link out of Story 1.5 (its Never section + Design Notes: it belongs to `bmad-switch::repoint_links`, shared with `planning-artifacts`), and today's operational mitigation is running `bmad-switch` inside the home (auto-memory `feedback_bmad_loop_worktree_needs_switch_and_backlink.md`). Needs a product decision: either a later Marshal story ports `repoint_links`' implementation-artifacts half (e.g. into 1.6/1.7's surface), or the FR-3 claim "every consumer sees the same path" is formally narrowed to nested-path consumers.

  status: open

## DW-4-2-1 — `marshal teardown` reports every landed story as an unreachable promotion for …

- source_spec: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-4-2-teardown-reachability-and-spec-recovery-assistance.md`
  summary: `marshal teardown <slug>` for a project whose planning tree no longer exists refuses with `MRS-TEARDOWN-003` naming **every** story that has ever landed on `main` as an unreachable promotion — none of which is at risk. `cli/deploy.py::_scan_promotions` derives the durable-story set from `main`'s merge subjects (repo-wide, not project-scoped, since the composed policy falls back to the default `merge_subject_template` when the project has no policy file) but resolves each story's spec at `_bmad-output/projects/<slug>/planning-artifacts/specs/`. When that directory is absent, every durable key lands in `plan.missing_spec_keys` and is reported as unreachable.
  evidence: Reproduced live 2026-08-08 while retiring the dissolved `pyforge-genesis` loop home. `unreachable_promotions_for_slug(root, "pyforge-genesis")` returns **26** keys — `1.3, 1.4, 2.1, 2.3, 2.7, 3.8, 4.1-4.10, 5.2-5.6, 6.1-6.5` — while the identical call for `"pyforge-marshal"` returns **0**. Same git history, same merge subjects, same spec files: all 50 of Marshal's story specs are tracked under `pyforge-marshal/planning-artifacts/specs/` and every one resolves. The 26 are Marshal's own landed stories being looked up under a slug whose tree was archived. Confirmed by inspection of `cli/deploy.py:602-603` (`specs_dir` is built by string-joining `project_slug`) and `:699-705` (`missing_spec_keys` folded into the unreachable set).
  impact: A safety refusal that cries wolf on 26 provably-safe stories is worse than no refusal — the documented override (`--force --abandon <26 keys>`) trains the operator to abandon a list they cannot practically verify, which is exactly the trust erosion AD-27's "every widening is recorded" discipline exists to prevent. It also makes tearing down any retired project impossible without that override.
  candidate fix: scope the durable-story scan to the project (or treat "project planning tree absent" as a distinct, non-blocking state — a project with no specs directory has no promotions to lose, which is a different fact from "26 promotions are missing their specs"). Worth deciding alongside the `--abandon` UX: it currently accepts a space-separated list but silently rejects the comma-separated form the refusal message's own rendering suggests.

  status: open

  verified: 2026-08-08 — found and reproduced during the genesis retirement; the teardown was completed with `--force --abandon` only after proving the 0-vs-26 asymmetry above. Supersedes the read recorded in auto-memory `project_genesis_teardown_deferred_2026-08-08.md`, which concluded the 26 keys were "stale artifacts of an already-completed retirement (pre-split planning-phase epics)" — they are not; they are Marshal's current, shipped stories.
